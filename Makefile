.PHONY: test scrape fairs rank refresh dashboard-data serve clean

PYTHON ?= python3
YEAR ?= 2027
FAIR_DAYS ?= 180
LISTINGS ?= data/all_internships.json
FAIRS ?= data/career_fair_events.json
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

fairs:
	mkdir -p $(dir $(FAIRS))
	$(PYTHON) src/fetch_career_fair_events.py --days $(FAIR_DAYS) --out $(FAIRS)

rank:
	$(PYTHON) src/rank_listings.py --listings $(LISTINGS) --profile $(PROFILE) \
		--career-fair-events $(FAIRS) --out $(SHORTLIST) --top $(TOP)

# The one command to run whenever ANY input might have changed (new postings,
# new campus-visit events, or an edited profile.json) - re-scrapes everything
# and re-ranks in one shot, so the shortlist is never left stale relative to
# its inputs. This is what "update the list" should mean day to day.
refresh: scrape fairs rank dashboard-data
	@echo "Refreshed $(SHORTLIST) and dashboard/data.json"

dashboard-data:
	$(PYTHON) src/build_dashboard_data.py --shortlist $(SHORTLIST) --applications-root $(APPLICATIONS_ROOT) --out dashboard/data.json

serve: dashboard-data
	cd dashboard && $(PYTHON) -m http.server $(PORT) --bind 127.0.0.1

clean:
	rm -f dashboard/data.json
	find . -name "__pycache__" -type d -exec rm -rf {} +
