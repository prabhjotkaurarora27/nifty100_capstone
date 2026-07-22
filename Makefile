.PHONY: help install load ratios test report dashboard api clean reset

help:
	@echo ""
	@echo "  Nifty 100 Capstone — Quick Reference Targets"
	@echo "  ──────────────────────────────────────────────"
	@echo "  make load       Load raw files into db/nifty100.db"
	@echo "  make ratios     Generate and populate financial_ratios table"
	@echo "  make test       Run all 250 pytest unit tests (HTML report)"
	@echo "  make report     Generate tearsheet, sector, and portfolio PDFs"
	@echo "  make dashboard  Launch Streamlit dashboard on localhost:8501"
	@echo "  make api        Launch FastAPI REST server on localhost:8000"
	@echo "  make clean      Remove cache (.pyc) and temporary artifacts"
	@echo ""

install:
	venv/bin/pip install -r requirements.txt

load:
	PYTHONPATH=. venv/bin/python3 src/etl/load_pipeline.py

ratios:
	PYTHONPATH=. venv/bin/python3 src/analytics/ratios.py

test:
	PYTHONPATH=. venv/bin/pytest tests/ --html=reports/pytest_report.html -v

report:
	PYTHONPATH=. venv/bin/python3 src/reports/batch_generator.py

dashboard:
	venv/bin/streamlit run src/dashboard/app.py

api:
	venv/bin/uvicorn src.api.main:app --port 8000 --reload

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
