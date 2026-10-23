"""DHIS2 Web API helpers for the e2e suite: HTTP client, app install, the
dataStore record of what a run creates, seeding and cleanup.

Since DHIS2 2.40 a normal metadata save rejects duplicate translations
(E1106), so duplicates are seeded with `POST /api/metadata?skipValidation=true`.
Every object gets a run-unique name and a client-side UID, and the UIDs are
written to the dataStore record before the objects are created
(TESTING.md in reference-tool-conventions, "Seeding and cleanup").
"""

import base64
import json
import random
import string
import urllib.error
import urllib.parse
import urllib.request
import zipfile

STATE_NAMESPACE = "e2e-state"
STATE_KEY = "tool-translation-deduplicator"
NAME_PREFIX = "E2E tool-translation-deduplicator"

# Deletion order: objects that reference others go first.
DELETE_ORDER = [
    "users",
    "userRoles",
    "maps",
    "dataSets",
    "dataElements",
    "options",
    "optionSets",
    "categoryCombos",
    "categories",
    "categoryOptions",
]
DELETE_PASSES = 3

# Fields that change on every save; ignored when comparing objects.
VOLATILE_FIELDS = {
    "translations",
    "lastUpdated",
    "lastUpdatedBy",
    "created",
    "createdBy",
    "version",
}


class ApiError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status


class Dhis2:
    def __init__(self, base_url, user, password):
        self.base_url = base_url.rstrip("/")
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.auth = f"Basic {token}"

    def request(self, method, path, body=None, content_type="application/json"):
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/{path}",
            method=method,
            data=data,
            headers={"Authorization": self.auth, "Content-Type": content_type},
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as error:
            raise ApiError(error.code, error.read().decode(errors="replace"))

    def get(self, path):
        return self.request("GET", path)[1]

    def session_cookie(self):
        """Log in with basic auth and return the session cookie, so a
        browser context can start logged in."""
        req = urllib.request.Request(
            f"{self.base_url}/api/me", headers={"Authorization": self.auth}
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            for header in response.headers.get_all("Set-Cookie") or []:
                name, _, value = header.split(";", 1)[0].partition("=")
                if "JSESSIONID" in name:
                    return name.strip(), value.strip()
        raise RuntimeError("No JSESSIONID cookie returned by /api/me")


def new_uid():
    first = random.choice(string.ascii_letters)
    rest = "".join(random.choices(string.ascii_letters + string.digits, k=10))
    return first + rest


def read_manifest(zip_path):
    with zipfile.ZipFile(zip_path) as bundle:
        return json.loads(bundle.read("manifest.webapp"))


def install_app(api, zip_path, manifest_name):
    """Install the bundle and return the key the server gave it."""
    boundary = "e2e" + new_uid()
    with open(zip_path, "rb") as handle:
        payload = handle.read()
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="app.zip"\r\n'
        "Content-Type: application/zip\r\n\r\n"
    ).encode() + payload + f"\r\n--{boundary}--\r\n".encode()
    # 204 on 2.41 and earlier, 201 on 2.42 and later
    api.request(
        "POST", "apps", body, content_type=f"multipart/form-data; boundary={boundary}"
    )
    for app in api.get("apps"):
        if app.get("name") == manifest_name:
            return app["key"]
    raise RuntimeError(f"Installed app {manifest_name!r} not found in /api/apps")


def uninstall_app(api, key):
    try:
        api.request("DELETE", f"apps/{urllib.parse.quote(key)}")
    except ApiError as error:
        if error.status != 404:
            raise


# --- state record -----------------------------------------------------------


def read_state(api):
    try:
        return api.get(f"dataStore/{STATE_NAMESPACE}/{STATE_KEY}")
    except ApiError as error:
        if error.status == 404:
            return None
        raise


def write_state(api, state):
    path = f"dataStore/{STATE_NAMESPACE}/{STATE_KEY}"
    try:
        api.request("PUT", path, state)
    except ApiError as error:
        if error.status != 404:
            raise
        api.request("POST", path, state)


def delete_state(api):
    try:
        api.request("DELETE", f"dataStore/{STATE_NAMESPACE}/{STATE_KEY}")
    except ApiError as error:
        if error.status != 404:
            raise


def delete_objects(api, objects):
    """Delete the recorded objects, dependants first. Returns the objects
    that could not be deleted."""
    remaining = sorted(
        objects,
        key=lambda o: DELETE_ORDER.index(o["type"])
        if o["type"] in DELETE_ORDER
        else len(DELETE_ORDER),
    )
    for _ in range(DELETE_PASSES):
        failed = []
        for obj in remaining:
            try:
                api.request("DELETE", f"{obj['type']}/{obj['id']}")
            except ApiError as error:
                if error.status != 404:
                    failed.append({**obj, "error": str(error)})
        remaining = failed
        if not remaining:
            break
    return remaining


def clean_previous_run(api):
    """Delete whatever an earlier, interrupted run left behind."""
    state = read_state(api)
    if not state:
        return []
    leftovers = delete_objects(api, state.get("objects", []))
    if leftovers:
        raise RuntimeError(f"Could not delete leftovers of an earlier run: {leftovers}")
    delete_state(api)
    return state.get("objects", [])


# --- seeding ----------------------------------------------------------------


def translations(locale, prop, values):
    return [{"locale": locale, "property": prop, "value": v} for v in values]


def import_metadata(api, bundle):
    _, report = api.request(
        "POST",
        "metadata?importStrategy=CREATE_AND_UPDATE&atomicMode=NONE&skipValidation=true",
        bundle,
    )
    errors = [
        error.get("message")
        for type_report in report.get("response", report).get("typeReports", [])
        for object_report in type_report.get("objectReports", [])
        for error in object_report.get("errorReports", [])
    ]
    if errors:
        raise RuntimeError(f"Metadata import failed: {errors}")


def plan_seed(run_id, xss_value):
    """Build the run's objects with client-side UIDs. Returns the import
    stages (imported in order) and the expected duplicates per object."""
    prefix = f"{NAME_PREFIX} {run_id}"
    uid = {key: new_uid() for key in (
        "co", "cat", "cc", "de_a", "de_b", "de_locked", "ds", "os", "opt",
        "map", "role", "user",
    )}

    def named(key, label, **fields):
        return {"id": uid[key], "name": f"{prefix} {label}", **fields}

    def short(label):
        # shortName is capped at 50 characters
        return f"E2E {run_id} {label}"[:50]

    de_fields = {
        "valueType": "NUMBER",
        "domainType": "AGGREGATE",
        "aggregationType": "SUM",
    }
    de_a_dups = translations("fr", "NAME", ["Doublon A", "Doublon B"]) + translations(
        "fr", "SHORT_NAME", ["Abrégé A", "Abrégé B"]
    )
    de_b_dups = translations("fr", "NAME", [xss_value, "Texte simple"]) + translations(
        "pt", "NAME", ["Nome 1", "Nome 2", "Nome 3"]
    )
    base = {
        "categoryOptions": [named("co", "category option", shortName=short("co"),
            translations=translations("fr", "NAME", ["Option 1", "Option 2"]))],
        "categories": [named("cat", "category", shortName=short("cat"),
            dataDimensionType="DISAGGREGATION", categoryOptions=[{"id": uid["co"]}])],
        "categoryCombos": [named("cc", "category combo",
            dataDimensionType="DISAGGREGATION", categories=[{"id": uid["cat"]}])],
        "dataElements": [
            named("de_a", "data element A", shortName=short("de A"),
                  translations=de_a_dups, **de_fields),
            named("de_b", "data element B", shortName=short("de B"),
                  translations=de_b_dups, **de_fields),
            # read-only to everyone without ALL: used for the permission test
            named("de_locked", "data element read-only", shortName=short("de RO"),
                  sharing={"public": "r-------", "external": False, "users": {},
                           "userGroups": {}},
                  publicAccess="r-------",
                  translations=translations("fr", "NAME", ["Verrou 1", "Verrou 2"]),
                  **de_fields),
        ],
        "optionSets": [named("os", "option set", valueType="TEXT",
            options=[{"id": uid["opt"]}],
            translations=translations("fr", "NAME", ["Liste 1", "Liste 2"]))],
        "options": [named("opt", "option", code=f"E2E_{run_id}",
            optionSet={"id": uid["os"]}, sortOrder=1,
            translations=translations("fr", "NAME", ["Choix 1", "Choix 2"]))],
        "maps": [named("map", "map", latitude=0, longitude=0, zoom=3,
            translations=translations("fr", "NAME", ["Carte 1", "Carte 2"]))],
    }
    # Data sets are imported on their own: 2.42.7 rejects them in a bundle
    # with their data elements (null DataSet.periodType).
    data_sets = {
        "dataSets": [named("ds", "data set", shortName=short("ds"),
            periodType="Monthly",
            dataSetElements=[{"dataElement": {"id": uid["de_a"]}, "dataSet": {"id": uid["ds"]}},
                             {"dataElement": {"id": uid["de_b"]}, "dataSet": {"id": uid["ds"]}}],
            translations=translations("fr", "NAME", ["Ensemble 1", "Ensemble 2"]))],
    }
    return uid, [base, data_sets]


def records_for(uid):
    return [
        {"type": t, "id": uid[k]}
        for t, k in (
            ("users", "user"), ("userRoles", "role"), ("maps", "map"),
            ("dataSets", "ds"), ("dataElements", "de_a"), ("dataElements", "de_b"),
            ("dataElements", "de_locked"), ("options", "opt"), ("optionSets", "os"),
            ("categoryCombos", "cc"), ("categories", "cat"), ("categoryOptions", "co"),
        )
    ]


def seed_coc_duplicates(api, category_combo_id):
    """Category option combos are generated by the server; give the run's
    one combo duplicate translations. It is deleted with its category combo."""
    path = f"categoryCombos/{category_combo_id}?fields=categoryOptionCombos[id]"
    if not api.get(path)["categoryOptionCombos"]:
        update = f"maintenance/categoryOptionComboUpdate/categoryCombo/{category_combo_id}"
        try:
            api.request("POST", update)
        except ApiError as error:
            # 2.41 only accepts PUT on this endpoint
            if error.status != 405:
                raise
            api.request("PUT", update)
    combos = api.get(f"categoryCombos/{category_combo_id}?fields=categoryOptionCombos[id]")
    coc_id = combos["categoryOptionCombos"][0]["id"]
    owner = api.get(f"categoryOptionCombos/{coc_id}?fields=:owner")
    owner["translations"] = translations("fr", "NAME", ["Combinaison 1", "Combinaison 2"])
    api.request(
        "POST",
        "metadata?importStrategy=UPDATE&atomicMode=NONE&skipValidation=true",
        {"categoryOptionCombos": [owner]},
    )
    return coc_id


def create_low_privilege_user(api, uid, run_id, password, app_key):
    """A user who can open the app but has no metadata authorities.
    DHIS2 names an app's authority M_ plus the key without hyphens
    (/api/authorities, which would list it, returns 500 on 2.41.10)."""
    authorities = ["M_" + app_key.replace("-", "")]
    username = f"e2e-ttd-{run_id.lower()}"
    import_metadata(api, {
        "userRoles": [{"id": uid["role"], "name": f"{NAME_PREFIX} {run_id} role",
                       "authorities": authorities}],
    })
    api.request("POST", "users", {
        "id": uid["user"], "username": username, "password": password,
        "firstName": "E2E", "surname": f"Translation dedup {run_id}",
        "userRoles": [{"id": uid["role"]}],
    })
    return username


def duplicates_of(api, collection, object_id):
    """Read back an object's duplicate groups: {(locale, property): [values]}."""
    stored = api.get(f"{collection}/{object_id}?fields=translations").get("translations", [])
    groups = {}
    for t in stored:
        groups.setdefault((t["locale"], t["property"]), []).append(t["value"])
    return {key: values for key, values in groups.items() if len(values) > 1}


def owner_snapshot(api, collection, object_id):
    return normalise(api.get(f"{collection}/{object_id}?fields=:owner"))


def normalise(value):
    if isinstance(value, dict):
        return {k: normalise(v) for k, v in sorted(value.items()) if k not in VOLATILE_FIELDS}
    if isinstance(value, list):
        return sorted((normalise(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True))
    return value
