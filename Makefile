.PHONY: install test benchmark compile web-build check

install:
	python -m pip install -r requirements.txt
	cd apps/web && npm ci

test:
	PYTHONPATH=. pytest -q

benchmark:
	PYTHONPATH=. python -c 'import asyncio; from services.evaluation.evaluator import SystemEvaluator; print(asyncio.run(SystemEvaluator.evaluate_full_gridlens()).metrics.json())'

compile:
	python -m compileall -q domain services apps

web-build:
	cd apps/web && npm run build

check: compile test web-build
