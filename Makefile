init:
	pip install -r requirements.txt

testk:
	python3 -m pytest -vsrA tests/* -k $(filter-out $@, $(MAKECMDGOALS)) -W ignore::DeprecationWarning -W ignore::FutureWarning --log-cli-level=DEBUG

testx:
	python3 -m pytest -vsx tests/* -W ignore::DeprecationWarning -W ignore::FutureWarning --log-cli-level=DEBUG

test:
	python3 -m pytest -vsrA tests/* -W ignore::DeprecationWarning -W ignore::FutureWarning --log-cli-level=DEBUG

.PHONY: init test