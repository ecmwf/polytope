init:
	pip install -r requirements.txt

testk:
	python3 -m pytest -vsrA tests/* -k $(filter-out $@, $(MAKECMDGOALS)) -W ignore::DeprecationWarning -W ignore::FutureWarning --log-cli-level=DEBUG

testx:
	python3 -m pytest -vsx tests/* -W ignore::DeprecationWarning -W ignore::FutureWarning --log-cli-level=DEBUG

test:
	python3 -m pytest -vsrA tests/* -W ignore::DeprecationWarning -W ignore::FutureWarning --log-cli-level=DEBUG

examples:
	python3 -m pytest -vsrA examples/* -W ignore::DeprecationWarning -W ignore::FutureWarning --log-cli-level=DEBUG

performance:
	python3 -m pytest -vsrA performance/* -W ignore::DeprecationWarning -W ignore::FutureWarning --log-cli-level=DEBUG

docs:
	mkdocs build
	mkdocs serve

.PHONY: init test