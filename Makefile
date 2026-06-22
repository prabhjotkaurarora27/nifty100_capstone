.PHONY: help setup install schema load inspect validate review fix ratios test report dashboard api clean reset

help:
	@echo ""
	@echo "  Nifty 100 Capstone — available targets"
	@echo "  ────────────────────────────────────────"
	@echo "  install    pip install -r requirements.txt"
	@echo "  schema     Create SQLite schema (db/nifty100.db)"
	@echo "  load       Reset DB + load all 12 source files + verify row counts"
	@echo "  inspect    Inspect data/raw/ files (columns, row counts)"
	@echo "  validate   Run 16 DQ rules → output/validation_failures.csv"
	@echo "  review     Sample 5 companies, write manual_review_report.txt"
	@echo "  fix        Retry ERROR/SKIPPED files from load_audit.csv"
	@echo "  ratios     Compute financial ratios"
	@echo "  test       Run pytest (tests/etl/)"
	@echo "  dashboard  Launch Streamlit dashboard"
	@echo "  api        Start Flask API server"
	@echo "  clean      Remove __pycache__, output CSVs"
	@echo "  reset      Drop and recreate nifty100.db"
	@echo ""

install:
	pip install -r requirements.txt

schema:
	python db/init_db.py

load:
	python src/etl/load_pipeline.py

inspect:
	python src/etl/file_inspector.py

validate:
	python src/etl/validator.py

review:
	python src/etl/manual_review.py

fix:
	python src/etl/fix_loader.py

ratios:
	python src/etl/normaliser.py

test:
	python -m pytest tests/etl/ --tb=short -q --cov=src/etl --cov-report=term-missing

dashboard:
	streamlit run src/dashboard/app.py

api:
	python src/api/app.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

reset:
	rm -f db/nifty100.db
	$(MAKE) schema
