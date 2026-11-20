"""Content-only parsing: never propagate repository or bundle metadata to copies."""
import hashlib
import re
import yaml

PARSER_VERSION = "2"
STANDARD_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}


class DuplicateKey(yaml.YAMLError):
    pass


class FrontmatterLoader(getattr(yaml, "CSafeLoader", yaml.SafeLoader)):
    def construct_mapping(self, node, deep=False):
        # YAML merge overrides are legal; repeated explicitly declared keys are not.
        keys = set()
        for key, _ in node.value:
            if key.tag == "tag:yaml.org,2002:merge":
                continue
            value = self.construct_object(key, deep=deep)
            try:
                if value in keys:
                    raise DuplicateKey("Repeated explicit YAML key")
                keys.add(value)
            except TypeError as exc:
                raise yaml.YAMLError("Unhashable YAML key") from exc
        return super().construct_mapping(node, deep=deep)


def value_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "mapping"
    if isinstance(value, list):
        return "list"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__


def field_state(meta, key, status):
    if status not in ("parsed", "no_frontmatter"):
        return "unknown", None
    if key not in meta:
        return "absent", None
    value = meta[key]
    if value is None or (isinstance(value, str) and not value.strip()):
        return "empty", None
    if not isinstance(value, str):
        return "invalid_type", None
    return "present", value.strip()


def parse_content(content, file_sha, fetched):
    if not fetched or content is None:
        return "not_fetched", {}, None
    raw = content.encode("utf-8")
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blob != file_sha:
        return "hash_mismatch", {}, None
    sha256 = hashlib.sha256(raw).hexdigest()
    text = content.lstrip("\ufeff")
    opening = re.match(r"\A---[ \t]*\r?\n", text)
    if not opening:
        if text.lstrip().startswith("---"):
            return "malformed_opening", {}, sha256
        return "no_frontmatter", {}, sha256
    closing = re.search(r"^(?:---|\.\.\.)[ \t]*\r?$", text[opening.end():], re.MULTILINE)
    if not closing:
        return "unclosed_frontmatter", {}, sha256
    header = text[opening.end():opening.end() + closing.start()]
    try:
        meta = yaml.load(header, Loader=FrontmatterLoader)
    except DuplicateKey:
        return "duplicate_yaml_keys", {}, sha256
    except (yaml.YAMLError, RecursionError, ValueError, OverflowError):
        return "invalid_yaml", {}, sha256
    if not isinstance(meta, dict):
        return "non_mapping_yaml", {}, sha256
    if not all(isinstance(key, str) for key in meta):
        return "non_string_keys", {}, sha256
    return "parsed", meta, sha256


def fields(meta):
    # Keep nesting explicit: metadata.author is not a top-level author field.
    for key, value in meta.items():
        yield "top", key, value_type(value), key in STANDARD_FIELDS
        if key == "metadata" and isinstance(value, dict):
            for child, child_value in value.items():
                if isinstance(child, str):
                    yield "metadata", child, value_type(child_value), False
