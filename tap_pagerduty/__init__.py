#!/usr/bin/env python3
import os
import json
import singer
import asyncio
import concurrent.futures
from singer import utils, metadata
from singer.catalog import Catalog, CatalogEntry, Schema

from .sync import PagerdutyAuthentication, PagerdutyClient, PagerdutySync

REQUIRED_CONFIG_KEYS = ["start_date",
                        "api_token"]
LOGGER = singer.get_logger()

# map of schema name with their primary key
SCHEMA_PRIMARY_KEYS = { 
    "incidents": ["id"],
    "alerts": ["id"],
    "escalation_policies": ["id"],
    "services": ["id"],
    "teams": ["id"],
    "users": ["id"],
    "vendors": ["id"]
}

def get_abs_path(path):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)

def load_schema(tap_stream_id):
    path = "schemas/{}.json".format(tap_stream_id)
    schema = utils.load_json(get_abs_path(path))
    refs = schema.pop("definitions", {})
    if refs:
        singer.resolve_schema_references(schema, refs)
    return schema

def generate_metadata(schema_name, schema):
    pk_fields = SCHEMA_PRIMARY_KEYS[schema_name]
    mdata = metadata.new()
    mdata = metadata.write(mdata, (), 'table-key-properties', pk_fields)

    for field_name in schema['properties'].keys():
        if field_name in pk_fields:
            mdata = metadata.write(mdata, ('properties', field_name), 'inclusion', 'automatic')
        else:
            mdata = metadata.write(mdata, ('properties', field_name), 'inclusion', 'available')

    return metadata.to_list(mdata)

def discover():
    streams = []

    for schema_name in SCHEMA_PRIMARY_KEYS.keys():

        schema = load_schema(schema_name)
        stream_metadata = generate_metadata(schema_name, schema)
        stream_key_properties = SCHEMA_PRIMARY_KEYS[schema_name]

        # create and add catalog entry
        catalog_entry = {
            'stream': schema_name,
            'tap_stream_id': schema_name,
            'schema': schema,
            'metadata' : stream_metadata,
            'key_properties': stream_key_properties
        }
        streams.append(catalog_entry)

    return {'streams': streams}

def create_sync_tasks(config, state, catalog):
    auth = PagerdutyAuthentication(config["api_token"])
    client = PagerdutyClient(auth)
    sync = PagerdutySync(client, state, config)

    sync_tasks = (sync.sync(stream['tap_stream_id'], stream['schema'])
                  for stream in catalog['streams'])

    return asyncio.gather(*sync_tasks)

def sync(config, state, catalog):
    loop = asyncio.get_event_loop()
    try:
        tasks = create_sync_tasks(config, state, catalog)
        loop.run_until_complete(tasks)
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

@utils.handle_top_exception(LOGGER)
def main():
    # Parse command line arguments
    args = utils.parse_args(REQUIRED_CONFIG_KEYS)

    # If discover flag was passed, run discovery mode and dump output to stdout
    if args.discover:
        catalog = discover()
        print(json.dumps(catalog, indent=2))
    # Otherwise run in sync mode
    else:
        if args.catalog:
            catalog = args.catalog
        else:
            catalog = discover()

        config = args.config
        state = {
            "bookmarks": {

            }
        }
        state.update(args.state)

        sync(config, state, catalog)

if __name__ == "__main__":
    main()
