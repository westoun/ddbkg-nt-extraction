#!/usr/bin/env python3

from multiprocessing import Queue
import rdflib
import re
from typing import Any, Dict, List
from urllib import parse
from xml.etree import ElementTree

from .interface import Extractor
from src.types_ import XmlObject, NTriplesResult

PREFIXES = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "ore": "http://www.openarchives.org/ore/terms/",
    "edm": "http://www.europeana.eu/schemas/edm/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dcterms": "http://purl.org/dc/terms/",
    "cidoc": "http://www.cidoc-crm.org/rdfs/cidoc_crm_v5.0.2_english_label.rdfs#",
    "ddbedm": "http://www.deutsche-digitale-bibliothek.de/edm/",
    "ddbitem": "http://www.deutsche-digitale-bibliothek.de/item/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
}


def create_id_map(xml: str) -> Dict:
    matches = re.findall(
        r"<([^<^>]+)ns[0-9]\:about\=(?:\'|\")([0-9A-Z ]{32})(?:\'|\")[^<^>]*>", xml
    )

    id_map = {}
    for context, id in matches:
        parent: str = context.split(" ")[0]

        if not parent.split(":")[-1][0].isupper():
            continue

        parent = parent.split(":")[-1]

        id_map[id] = f"http://www.deutsche-digitale-bibliothek.de/{parent}/{id}"

    return id_map


def create_url_map(xml: str) -> Dict:
    matches = re.findall(
        r"(?:\'|\"|\>)(?:http|ftp|https)\:\/\/[^<^>^\"^\']+(?:\'|\"|\<)", xml
    )

    url_map = {}
    for match in matches:
        url = match[1:-1]

        # Handle edge case where list of multiple urls is used
        # as one value.
        if len(re.findall(r"(?:http|ftp|https)://", url)) > 1:
            continue

        sanitized_url = parse.quote(url, safe="/:#")
        if url != sanitized_url:
            url_map[url] = sanitized_url

    return url_map


class RdflibExtractor(Extractor):
    """Parse xml objects from text according to the parsing
    logic of Ann Tan.
    """

    in_queue: "Queue[XmlObject]"
    out_queue: "Queue[NTriplesResult]"

    def __init__(
        self, in_queue: "Queue[XmlObject]", out_queue: "Queue[NTriplesResult]"
    ) -> None:
        self.in_queue = in_queue
        self.out_queue = out_queue

    def run(self) -> None:
        while True:
            xml_object: XmlObject = self.in_queue.get()

            if xml_object is None:
                self.in_queue.put(None)  # Alert other workers
                break

            xml = xml_object.text

            id_map = create_id_map(xml)
            url_map = create_url_map(xml)

            graph = rdflib.Graph()
            for k, v in PREFIXES.items():
                graph.namespace_manager.bind(k, rdflib.URIRef(v))

            doc = ElementTree.fromstring(xml)
            edm = doc.find(".//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF")
            graph.parse(data=ElementTree.tostring(edm), format="application/rdf+xml")
            ntriples: str = graph.serialize(format="ntriples")

            for id in id_map:
                ntriples = ntriples.replace(id, id_map[id])

            for url in url_map:
                ntriples = ntriples.replace(url, url_map[url])

            parsing_result = NTriplesResult(
                ntriples=ntriples, object_id=xml_object.object_id
            )
            self.out_queue.put(parsing_result)

        self.out_queue.put(None)
