test:
	uv run cityfeel/manage.py test cityfeel

generate_spec:
	uv run cityfeel/manage.py spectacular --file cityfeel/api/spec/schema.yml