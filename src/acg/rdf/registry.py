#!/usr/bin/env python3
"""Reusable RDF mapping of selected metadata records; CLI builds the unified graph."""

import json
from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF, URIRef


from acg.paths import REGISTRY as ROOT
DATA_DIR = ROOT / "data"
ACG = Namespace("urn:acg:ontology:")
DATA = Namespace("urn:acg:metadata:")
SCHEMA = Namespace("https://schema.org/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
PROV = Namespace("http://www.w3.org/ns/prov#")


def rows(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def iri(kind, identifier):
    return DATA[f"{kind}/{quote(str(identifier), safe='-._~')}" ]


def add_source(graph, url, revision=None):
    if not url:
        return None
    source = iri("source", url)
    graph.add((source, RDF.type, ACG.SourceDocument))
    graph.add((source, RDF.type, PROV.Entity))
    graph.add((source, SCHEMA.url, URIRef(url)))
    if revision:
        graph.add((source, ACG.revision, Literal(revision)))
    return source


def add_value(graph, subject, predicate, value):
    if value is None or value == "" or value == [] or value == {}:
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            add_value(graph, subject, predicate, item)
    elif isinstance(value, dict):
        graph.add((subject, predicate, Literal(json.dumps(value, ensure_ascii=False))))
    else:
        graph.add((subject, predicate, Literal(value)))


def build_graph(servers=None, tools=None, skills=None, annotations=None):
    graph = Graph()
    for prefix, namespace in (("acg", ACG), ("acgdata", DATA), ("schema", SCHEMA),
                              ("skos", SKOS), ("prov", PROV)):
        graph.bind(prefix, namespace)

    if servers is None:
        servers = [r for r in rows(DATA_DIR / "normalized/mcp_servers.jsonl")
                   if r.get("disposition") == "accepted"]
    if tools is None:
        tools = [r for r in rows(DATA_DIR / "normalized/mcp_tools.jsonl")
                 if r.get("disposition") == "accepted"]
    if skills is None:
        skills = [r for r in rows(DATA_DIR / "normalized/agent_skills.jsonl")
                  if r.get("disposition") == "accepted"]
    if annotations is None:
        annotations = rows(DATA_DIR / "enriched/capability_annotations.jsonl")

    for record in servers:
        entity = iri("server", record["server_id"])
        graph.add((entity, RDF.type, ACG.MCPServer))
        add_value(graph, entity, SCHEMA.name, record.get("name"))
        add_value(graph, entity, SCHEMA.description, record.get("description"))
        add_value(graph, entity, SCHEMA.softwareVersion, record.get("version"))
        add_value(graph, entity, SCHEMA.license, record.get("license"))
        add_value(graph, entity, ACG.transport, record.get("transport"))
        add_value(graph, entity, ACG.repositoryUrl, record.get("repository_url"))
        add_value(graph, entity, ACG.registryUrl, record.get("registry_url"))
        add_value(graph, entity, ACG.isLatest, record.get("is_latest"))
        source = add_source(graph, record.get("source_url"), record.get("source_revision"))
        if source:
            graph.add((entity, ACG.documentedBy, source))

    for record in tools:
        entity = iri("tool", record["tool_id"])
        parent = iri("server", record["server_id"])
        graph.add((entity, RDF.type, ACG.MCPTool))
        graph.add((parent, ACG.exposesTool, entity))
        add_value(graph, entity, SCHEMA.name, record.get("name"))
        add_value(graph, entity, SCHEMA.description, record.get("description"))
        add_value(graph, entity, ACG.requiredParameter, record.get("required_parameters"))
        add_value(graph, entity, ACG.readOnlyHint, record.get("read_only_hint"))
        add_value(graph, entity, ACG.inputSchemaDescription, record.get("input_schema"))
        add_value(graph, entity, ACG.schemaFormat, record.get("schema_format"))
        add_value(graph, entity, ACG.toolAnnotation, record.get("tool_annotations"))
        source = add_source(graph, record.get("source_url"), record.get("source_revision"))
        if source:
            graph.add((entity, ACG.documentedBy, source))
        schema_source = add_source(
            graph, record.get("input_schema_source_url"), record.get("source_revision")
        )
        if schema_source:
            graph.add((entity, ACG.documentedBy, schema_source))

    for record in skills:
        entity = iri("skill", record["skill_id"])
        graph.add((entity, RDF.type, ACG.AgentSkill))
        add_value(graph, entity, SCHEMA.name, record.get("name"))
        add_value(graph, entity, SCHEMA.description, record.get("description"))
        add_value(graph, entity, SCHEMA.license, record.get("license"))
        add_value(graph, entity, ACG.compatibility, record.get("compatibility"))
        add_value(graph, entity, ACG.dependency, record.get("dependencies"))
        add_value(graph, entity, ACG.allowedTool, record.get("allowed_tools"))
        add_value(graph, entity, ACG.hasScripts, record.get("has_scripts"))
        add_value(graph, entity, ACG.hasReferences, record.get("has_references"))
        add_value(graph, entity, ACG.hasAssets, record.get("has_assets"))
        add_value(graph, entity, ACG.repositoryUrl, record.get("repository_url"))
        add_value(graph, entity, ACG.skillPath, record.get("skill_path"))
        source = add_source(graph, record.get("source_url"), record.get("source_revision"))
        if source:
            graph.add((entity, ACG.documentedBy, source))

    tools_by_id = {r["tool_id"]: r for r in tools}
    for annotation in annotations:
        record = tools_by_id.get(annotation.get("tool_id"))
        if record is None:
            continue
        tool = iri("tool", annotation["tool_id"])
        action = annotation.get("capability_action")
        obj = annotation.get("capability_object")
        capability = iri("capability", f"{action}/{obj}")
        assertion = iri("assertion", annotation["annotation_id"])
        graph.add((capability, RDF.type, ACG.Capability))
        graph.add((capability, SKOS.prefLabel, Literal(f"{action} {obj}")))
        add_value(graph, capability, ACG.capabilityAction, action)
        add_value(graph, capability, ACG.capabilityObject, obj)
        graph.add((tool, ACG.hasCapabilityAssertion, assertion))
        graph.add((assertion, RDF.type, ACG.CapabilityAssertion))
        graph.add((assertion, ACG.assertedCapability, capability))
        graph.add((assertion, ACG.assertionMethod, ACG.inferred))
        add_value(graph, assertion, ACG.reviewStatus, annotation.get("review_status"))
        add_value(graph, assertion, ACG.evidenceType, annotation.get("evidence_type"))
        add_value(graph, assertion, ACG.stateChange, annotation.get("state_change"))
        add_value(graph, assertion, ACG.requiresAuthentication,
                  annotation.get("requires_authentication"))
        add_value(graph, assertion, ACG.evidenceText, annotation.get("evidence_text"))
        source = add_source(graph, annotation.get("evidence_source"), record.get("source_revision"))
        if source:
            graph.add((assertion, ACG.basedOnSource, source))

    return graph


