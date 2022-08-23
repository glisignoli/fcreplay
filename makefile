test:
	pytest

testsite:
	pipenv run pytest --runslow -s ./fcreplay/tests/test_functionality.py::TestFunctionality::test_site

testfunc:
	pipenv run pytest --runslow -s ./fcreplay/tests/test_functionality.py

build:
	docker-compose build
