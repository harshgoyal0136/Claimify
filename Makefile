.PHONY: setup smoke test eval bench demo
setup:
	pip install -r requirements.txt
smoke:
	python scripts/smoke_bedrock.py
test:
	pytest -q
eval:
	python scripts/eval.py --out reports/eval_latest.md
bench:
	python scripts/bench.py --files data/bench --runs 20 --out reports/latency_latest.md
demo:
	streamlit run claimshield/ui/app.py
