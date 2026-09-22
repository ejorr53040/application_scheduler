.PHONY: test scrape rank dashboard-data serve clean

PYTHON ?= python3
YEAR ?= 2027
LISTINGS ?= data/all_internships.json
PROFILE ?= data/profile.json
SHORTLIST ?= data/shortlist.json
APPLICATIONS_ROOT ?= data/applications
TOP ?= 50
PORT ?= 8420

test:
	$(PYTHON) -m unittest discover -s tests -v

scrape:
	mkdir -p $(dir $(LISTINGS))
	$(PYTHON) src/scrape_listings.py --year $(YEAR) --out $(LISTINGS)

rank:
	$(PYTHON) src/rank_listings.py --listings $(LISTINGS) --profile $(PROFILE) --out $(SHORTLIST) --top $(TOP)

dashboard-data:
	$(PYTHON) src/build_dashboard_data.py --shortlist $(SHORTLIST) --applications-root $(APPLICATIONS_ROOT) --out dashboard/data.json

serve: dashboard-data
	cd dashboard && $(PYTHON) -m http.server $(PORT) --bind 127.0.0.1

clean:
	rm -f dashboard/data.json
	find . -name "__pycache__" -type d -exec rm -rf {} +
