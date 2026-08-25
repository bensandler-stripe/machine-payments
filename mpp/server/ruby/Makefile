.PHONY: install run lint format typecheck test ci

BUNDLE ?= bundle
RUBY ?= ruby

install:
	$(BUNDLE) install

run:
	$(BUNDLE) exec $(RUBY) app.rb

lint:
	$(BUNDLE) exec standardrb

format:
	$(BUNDLE) exec standardrb --fix

typecheck:
	$(RUBY) -c app.rb

test:
	$(BUNDLE) exec $(RUBY) test/app_test.rb

ci: install lint typecheck test
