
from elasticsearch import Elasticsearch
import time
from string import  Template
from collections import  defaultdict

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INDEX_NAME, INDEX_TYPE = "movies_temp", "movies"

read_es = Elasticsearch()
time.sleep(2)

FACET_FIELDS = ["genre", "source", "language", "release_year", "country"]

FIND_DOCS_BY_QUERY = Template("""
{
  "size": $size,
  "query": {
    "bool" : {
        "should" : [
            {
                "match": {
                    "title" : "$search_query"
                }
            },
            {
                "match": {
                    "snippet" : "$search_query"
                }
            }
        ]
    }
  },
   "aggregations": {
      "genre": {
         "terms": {
            "field": "genre"
         }
      },
      "source": {
         "terms": {
            "field": "source"
         }
      },
      "release_year": {
         "terms": {
            "field": "release_year"
         }
      }
   },
    "highlight": {
        "pre_tags" : ["<font color='red'>"],
        "post_tags" : ["</font>"],
        "fields" : {
            "title" : {},
            "snippet" : {}
        }
    }
}
""")

FIND_DOCS_BY_QUERY_AND_FILTER = Template("""
{
  "size": $size,
  "query" : {
    "filtered" : {
          "filter" : {
            "bool" : {
                "must" : [
                    {
                      "term": {
                        "$filter_name": "$filter_value"
                      }
                    }
                ]
            }
          },
          "query": {
            "bool" : {
                "should" : [
                    {
                        "match": {
                            "title" : "$search_query"
                        }
                    },
                    {
                        "match": {
                            "snippet" : "$search_query"
                        }
                    }
                ]
            }
          }
    }
  },
   "aggregations": {
      "genre": {
         "terms": {
            "field": "genre"
         }
      },
      "source": {
         "terms": {
            "field": "source"
         }
      },
      "release_year": {
         "terms": {
            "field": "release_year"
         }
      }
   },
    "highlight": {
        "pre_tags" : ["<font color='red'>"],
        "post_tags" : ["</font>"],
        "fields" : {
            "title" : {},
            "snippet" : {}
        }
    }
}
""")

class SearchInput(object):

    def __init__(self, query, filter=None, max_results=20, facets_reqd=True):
        self.query = query
        self.max_results = max_results
        self.facets_reqd = facets_reqd
        self.filter = filter

    def __str__(self):
        return "(%s & %s)" % (self.query, self.filter)


class SearchResult(object):

    def __init__(self, id, score, image_url, title, source, original_url, snippet, genre):
        self.id = id
        self.score = score
        self.image_url = image_url
        self.title = title
        self.source = source
        self.original_url = original_url
        self.snippet = snippet
        self.genre = genre

    def __str__(self):
        return "(%s => %s)" % (self.title, self.snippet)


class SearchFacet(object):

    def __init__(self, attr_name, attr_value_map):
        self.attr_name = attr_name
        self.attr_value_map = attr_value_map

    def __str__(self):
        return "(%s => %s" % (self.attr_name, self.attr_value_map)


class SearchOutput(object):

    def __init__(self, search_results, search_facets):
        self.search_results = search_results
        self.search_facets = search_facets

    def __str__(self):
        return ("%s => %s") % (self.search_results, self.search_facets)


def get_field_value(source_doc, highlight_doc, field):
    value = ""

    if field in highlight_doc:
        value = highlight_doc.get(field)[0]
    else:
        value = source_doc[field]

    return value


def search(search_input):

    filter_name, filter_value = None, None
    search_template = None

    # Call this when facet based filtering used
    if search_input.filter:
        for key, val in search_input.filter.items():
            filter_name, filter_value = key, val

        search_template = FIND_DOCS_BY_QUERY_AND_FILTER.substitute(
                size=search_input.max_results,
                search_query=search_input.query,
                filter_name=filter_name,
                filter_value=filter_value
        )
    # Call it for simple text-based search
    else:
        search_template = FIND_DOCS_BY_QUERY.substitute(
                size=search_input.max_results,
                search_query=search_input.query
        )

    logger.info("Search Query : %s", search_template)

    results = read_es.search(index=INDEX_NAME, doc_type=INDEX_TYPE, body=search_template)
    raw_docs = results['hits']['hits']

    # Extract the search results
    search_results = []
    for doc in raw_docs:
        source_doc = doc['_source']
        highlight_doc = doc['highlight']
        id, score = doc['_id'], doc['_score']

        image_url = source_doc.get('image_url')
        title = get_field_value(source_doc, highlight_doc, 'title')
        source = source_doc['source']
        original_url = source_doc['url']
        snippet = get_field_value(source_doc, highlight_doc, 'snippet')
        genre = source_doc.get('genre')

        result = SearchResult(id, score, image_url, title, source, original_url, snippet, genre)
        search_results.append(result)

    # Extract the facets
    search_facets = []
    if search_input.facets_reqd:
        raw_aggs = results['aggregations']
        for facet in FACET_FIELDS:
            if raw_aggs.get(facet):
                facet_raw_values = raw_aggs[facet]['buckets']
                facet_counter = defaultdict()
                for value in facet_raw_values:
                    facet_value, facet_count = value['key'], value['doc_count']
                    facet_counter[facet_value] = facet_count

                facet_group = SearchFacet(facet, facet_counter)
                search_facets.append(facet_group)

    return SearchOutput(search_results, search_facets)

if __name__ == '__main__':
    input = SearchInput("hello world")
    output = search(input)
    logger.info("%s", str(output))