import psycopg2, json
conn = psycopg2.connect(host='127.0.0.1', port=5432, dbname='formulary_api_test', user='postgres', password='Number@56')
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
with open('sample_inputs.json') as f:
    data = json.load(f)
for r in data['route-mapping']['records']:
    cur.execute('INSERT INTO crm.route_mapping (mapping_id, route_of_administration_id) VALUES (%s,%s) ON CONFLICT DO NOTHING',
        (r['mapping_id'], r['route_of_administration_id']))
print('Inserted route-mapping records')
cur.execute('SELECT COUNT(*) FROM crm.route_mapping')
print('Total:', cur.fetchone()[0])
conn.close()
