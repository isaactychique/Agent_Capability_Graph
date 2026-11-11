#!/usr/bin/env python3
"""Convert harvested SQLite metadata into RDF using the ACG Turtle ontology."""

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD
from rdflib.namespace import OWL, RDFS


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "interim" / "metadata.sqlite3"
DEFAULT_ONTOLOGY = ROOT / "docs" / "acg_ontology.ttl"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "harvested_graph.ttl"
ACG = Namespace("urn:acg:ontology:")
DATA = Namespace("urn:acg:data:")
SCHEMA = Namespace("https://schema.org/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

ENTITY_TYPES = {
    "MCPServer": ACG.MCPServer,
    "Tool": ACG.MCPTool,
    "AgentSkill": ACG.AgentSkill,
}

# These mappings materialize only fields whose values fit the ontology term.
# Everything, including unmapped fields, is also retained as an observation.
OBSERVED_PROPERTIES = {
    "name": SCHEMA.name,
    "description": SCHEMA.description,
    "version": SCHEMA.softwareVersion,
    "license": SCHEMA.license,
    "transport": ACG.transport,
    "installation": ACG.installationMethod,
    "authentication": ACG.authenticationRequirement,
    "usage_conditions": ACG.activationCondition,
    "supported_platform": SCHEMA.runtimePlatform,
    "dependencies": ACG.dependency,
    "bundled_files": ACG.supportingFile,
}
STATUS_MAP = {
    "not_documented_in_frontmatter": ACG.notDocumented,
    "not_established_from_reviewed_sources": ACG.notDocumented,
}


def entity_uri(entity_id):
    return DATA["entity/" + quote(entity_id, safe="-._~")]


def source_uri(source_url):
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()
    return DATA["source/" + digest]


def observation_uri(entity_id, field, source_url):
    key = "\0".join((entity_id, field, source_url)).encode("utf-8")
    return DATA["observation/" + hashlib.sha256(key).hexdigest()]


def capability_uri(label):
    return DATA["capability/" + quote(label, safe="-._~")]


def literal_for(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return Literal(value, datatype=XSD.boolean)
    if isinstance(value, (dict, list)):
        return Literal(json.dumps(value, ensure_ascii=False), datatype=RDF.JSON)
    if isinstance(value, int):
        return Literal(value, datatype=XSD.integer)
    if isinstance(value, float):
        return Literal(value, datatype=XSD.double)
    return Literal(str(value))


def read_collection_date(connection):
    table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='collection_metadata'"
    ).fetchone()
    if not table:
        return None
    row = connection.execute(
        "SELECT value FROM collection_metadata WHERE key='collected_at'"
    ).fetchone()
    if not row:
        return None
    # Store the collection date, not the time at which RDF conversion runs.
    return date.fromisoformat(row[0][:10])


def load_records(connection):
    entities = connection.execute(
        "SELECT entity_id, entity_type, parent_server, revision FROM entity ORDER BY entity_id"
    ).fetchall()
    records = []
    for entity_id, entity_type, parent_server, revision in entities:
        rows = connection.execute(
            """SELECT field, value_json, evidence_status, source_url
               FROM metadata_observation WHERE entity_id=? ORDER BY field, source_url""",
            (entity_id,),
        ).fetchall()
        fields = []
        for field, value_json, status, source_url in rows:
            value = json.loads(value_json) if value_json is not None else None
            fields.append({"field": field, "value": value, "status": status, "source": source_url})
        records.append({"id": entity_id, "type": entity_type, "parent": parent_server,
                        "revision": revision, "fields": fields})
    return records


def add_source(graph, source_url, revision, collection_date):
    source = source_uri(source_url)
    graph.add((source, RDF.type, ACG.SourceDocument))
    graph.add((source, SCHEMA.url, URIRef(source_url.split("#L", 1)[0])))
    graph.add((source, ACG.sourceUrl, Literal(source_url)))
    graph.add((source, ACG.revision, Literal(revision)))
    if collection_date:
        graph.add((source, ACG.retrievedAt, Literal(collection_date, datatype=XSD.date)))
    return source


def add_direct_values(graph, resource, record, field_values):
    for field in ("name", "description", "version", "license", "transport",
                  "installation", "authentication", "usage_conditions"):
        value = field_values.get(field)
        prop = OBSERVED_PROPERTIES.get(field)
        if prop and isinstance(value, (str, int, float, bool)):
            graph.add((resource, prop, literal_for(value)))

    for field in ("dependencies", "bundled_files"):
        value = field_values.get(field)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    graph.add((resource, OBSERVED_PROPERTIES[field], Literal(item)))

    # The collector records these MCP hints in an annotations dictionary.
    annotations = field_values.get("annotations")
    if record["type"] == "Tool" and isinstance(annotations, dict):
        for name in ("readOnlyHint", "idempotentHint", "destructiveHint", "openWorldHint"):
            if isinstance(annotations.get(name), bool):
                graph.add((resource, ACG[name], literal_for(annotations[name])))


def build_graph(records, collection_date):
    graph = Graph()
    graph.bind("acg", ACG)
    graph.bind("acgdata", DATA)
    graph.bind("schema", SCHEMA)
    graph.bind("skos", SKOS)
    graph.bind("xsd", XSD)

    field_values = {
        record["id"]: {item["field"]: item["value"] for item in record["fields"]}
        for record in records
    }
    known_sources = {}

    # First create the harvested entities, source documents, and observations.
    for record in records:
        entity_type = ENTITY_TYPES.get(record["type"])
        if entity_type is None:
            raise ValueError(f"Unsupported harvested entity type: {record['type']}")
        resource = entity_uri(record["id"])
        graph.add((resource, RDF.type, entity_type))
        add_direct_values(graph, resource, record, field_values[record["id"]])

        for item in record["fields"]:
            source = known_sources.get(item["source"])
            if source is None:
                source = add_source(graph, item["source"], record["revision"], collection_date)
                known_sources[item["source"]] = source
            graph.add((resource, ACG.documentedBy, source))

            observation = observation_uri(record["id"], item["field"], item["source"])
            graph.add((observation, RDF.type, ACG.MetadataObservation))
            graph.add((observation, ACG.observesEntity, resource))
            graph.add((observation, ACG.observedFieldName, Literal(item["field"])))
            graph.add((observation, ACG.reviewedSource, source))
            raw_status = item["status"]
            graph.add((observation, ACG.evidenceStatus, Literal(raw_status)))
            normalized_status = STATUS_MAP.get(raw_status, ACG.present)
            graph.add((observation, ACG.observationStatus, normalized_status))
            property_uri = OBSERVED_PROPERTIES.get(item["field"])
            if property_uri:
                graph.add((observation, ACG.observedProperty, property_uri))
            observed_value = literal_for(item["value"])
            if observed_value is not None:
                graph.add((observation, ACG.hasObservedValue, observed_value))

    # Connect tools to their declared parent servers.
    for record in records:
        if record["type"] == "Tool" and record["parent"]:
            parent = entity_uri(record["parent"])
            tool = entity_uri(record["id"])
            if not any(item["id"] == record["parent"] and item["type"] == "MCPServer"
                       for item in records):
                raise ValueError(f"Tool {record['id']} refers to missing server {record['parent']}")
            graph.add((parent, ACG.exposesTool, tool))

    # Turn curator capability labels into explicit, traceable assertion nodes.
    for record in records:
        for item in record["fields"]:
            if item["field"] != "capabilities" or not isinstance(item["value"], list):
                continue
            subject = entity_uri(record["id"])
            source = known_sources[item["source"]]
            for label in item["value"]:
                if not isinstance(label, str) or not label.strip():
                    continue
                capability = capability_uri(label)
                graph.add((capability, RDF.type, ACG.Capability))
                graph.add((capability, SKOS.prefLabel, Literal(label)))
                assertion_key = f"{record['id']}|{label}|{item['source']}"
                assertion = DATA["capability-assertion/" + hashlib.sha256(
                    assertion_key.encode("utf-8")).hexdigest()]
                graph.add((subject, ACG.hasCapabilityAssertion, assertion))
                graph.add((assertion, RDF.type, ACG.CapabilityAssertion))
                graph.add((assertion, ACG.assertedCapability, capability))
                graph.add((assertion, ACG.assertionMethod, ACG.curatorMapped))
                graph.add((assertion, ACG.basedOnSource, source))

    return graph


def validate_graph(ontology, data_graph, records):
    """Perform useful application checks; this is not a full OWL reasoner."""
    errors = []
    declared_classes = set(ontology.subjects(RDF.type, OWL.Class))
    declared_properties = set(ontology.subjects(RDF.type, OWL.ObjectProperty))
    declared_properties.update(ontology.subjects(RDF.type, OWL.DatatypeProperty))
    used_types = set(data_graph.objects(None, RDF.type))
    for rdf_type in used_types:
        if str(rdf_type).startswith(str(ACG)) and rdf_type not in declared_classes:
            errors.append(f"Undeclared ACG class used: {rdf_type}")

    used_acg_predicates = {p for p in data_graph.predicates()
                           if str(p).startswith(str(ACG))}
    for predicate in used_acg_predicates - declared_properties:
        errors.append(f"Undeclared ACG property used: {predicate}")

    for record in records:
        resource = entity_uri(record["id"])
        if record["type"] == "Tool" and not (record["parent"] and
                (entity_uri(record["parent"]), ACG.exposesTool, resource) in data_graph):
            errors.append(f"Tool has no server link: {record['id']}")
        for item in record["fields"]:
            observation = observation_uri(record["id"], item["field"], item["source"])
            required = (ACG.observesEntity, ACG.observedFieldName,
                        ACG.observationStatus, ACG.reviewedSource)
            if any((observation, predicate, None) not in data_graph for predicate in required):
                errors.append(f"Incomplete metadata observation: {record['id']} / {item['field']}")

    for assertion in data_graph.subjects(RDF.type, ACG.CapabilityAssertion):
        for predicate in (ACG.assertedCapability, ACG.assertionMethod, ACG.basedOnSource):
            values = list(data_graph.objects(assertion, predicate))
            if len(values) != 1:
                errors.append(f"Capability assertion {assertion} needs exactly one {predicate}")

    # Check the declared domain/range expectations for project-local predicates.
    schema_graph = ontology + data_graph
    for predicate in used_acg_predicates:
        domains = list(ontology.objects(predicate, RDFS.domain))
        ranges = list(ontology.objects(predicate, RDFS.range))
        for subject, _, obj in data_graph.triples((None, predicate, None)):
            for domain in domains:
                if (subject, RDF.type, domain) not in data_graph:
                    errors.append(f"Domain mismatch for {predicate}: {subject} should be {domain}")
            for range_type in ranges:
                if str(range_type).startswith(str(ACG)) and (obj, RDF.type, range_type) not in schema_graph:
                    errors.append(f"Range mismatch for {predicate}: {obj} should be {range_type}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    try:
        ontology = Graph()
        ontology.parse(args.ontology, format="turtle")
        with sqlite3.connect(args.database) as connection:
            collection_date = read_collection_date(connection)
            records = load_records(connection)
        if not records:
            raise ValueError(f"No harvested entities found in {args.database}")
        data_graph = build_graph(records, collection_date)
        errors = validate_graph(ontology, data_graph, records)
        if errors:
            raise ValueError("RDF consistency checks failed:\n- " + "\n- ".join(errors))

        args.output.parent.mkdir(parents=True, exist_ok=True)
        data_graph.serialize(destination=args.output, format="turtle")
        # Parse the serialized output again to catch serialization/format errors.
        reparsed = Graph()
        reparsed.parse(args.output, format="turtle")
        print(f"Ontology parsed: {len(ontology)} triples")
        print(f"Harvested graph: {len(reparsed)} triples")
        print(f"Entities converted: {len(records)}")
        if collection_date is None:
            print("Note: collection date is unavailable in this SQLite snapshot.")
        print(f"Output: {args.output}")
    except Exception as error:
        raise SystemExit(f"RDF generation failed: {error}") from error


if __name__ == "__main__":
    main()
