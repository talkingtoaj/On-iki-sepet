# Speed vs Safety Rules

## For Core Logic and Database Code

* Move carefully and in very small steps
* Prefer test-first development
* Write the test before writing the implementation whenever possible
* Avoid changing working logic unless necessary
* Prioritize correctness, readability, and stability
* Be especially careful with financial calculations, account balances, and database migrations
* Keep the existing tested financial logic stable
* Do not rewrite working backend code unless there is a clear reason

## TDD Rules

* For important business logic, always start with a test
* First write a failing test that describes the expected behavior
* Then write the simplest code needed to pass the test
* Refactor only after the test is passing
* Do not add unnecessary logic before there is a test or clear requirement
* When fixing a bug, write a test that reproduces the bug first
* Keep tests readable and focused on one behavior at a time
* Prefer many small tests over one large unclear test
* Run tests often while developing
* Do not move to the next feature while important tests are failing

## Testing File Organization Rules

* Do not put all tests in one large `tests.py` file
* Use a `tests/` folder when a feature has multiple test types
* Split tests by responsibility: model, form, views, and business rules
* Use `tests/helpers.py` for shared test helpers
* Keep test file names clear and predictable

Preferred example:

```text
onikisepet/
    tests/
        __init__.py
        helpers.py
        test_category_model.py
        test_category_form.py
        test_category_views.py
```

For future features, follow the same pattern:

```text
test_account_model.py
test_account_form.py
test_account_views.py

test_transaction_model.py
test_transaction_form.py
test_transaction_views.py
test_transaction_business_rules.py
```

* Run the smallest relevant test file first
* Then run the full app test suite
* Do not move to the next feature until focused tests pass

## Clean Code Rules

* Write simple, readable, and maintainable code
* Prefer clear names over clever solutions
* Keep functions small and focused
* Avoid duplicated business logic
* Do not hide important logic inside templates
* Keep financial rules in Python code where they can be tested
* Use helper functions or services when logic is reused
* Make the code understandable for a junior developer
* Refactor carefully and only when tests protect the behavior

## Code Explanation Rules

* Every code change should include a clear explanation
* Explain what the code does in simple language
* Explain why this approach was chosen
* Explain how the code connects to the current feature or test
* When writing tests, explain what behavior the test protects
* When changing existing code, explain what changed and why
* Avoid unexplained code blocks
* Do not add unnecessary comments inside the code just to explain obvious lines
* Prefer explaining the code after the code block in plain language
* Comments inside the code should be used only when they make the logic clearer

## For Financial Rules

* Transfers must not be counted as income
* Transfers must not be counted as expenses
* Transfers should only be stored as money movements between accounts
* Income, expenses, and transfers must stay separate in reports and calculations
* Account balances must be calculated carefully and tested
* Financial correctness is more important than UI polish
* Reports must not mix transfers into income, expense, profit, or loss calculations

## For Django and User Interface Work

* It is acceptable to move faster and implement a complete vertical slice at once
* Prefer building a working end-to-end user flow when appropriate
* Do not unnecessarily slow down UI progress with overly fragmented steps
* Keep the existing tested calculation and database logic stable
* Reuse working backend code instead of rewriting it
* Keep Django templates simple and readable
* Do not put important financial logic directly inside templates
* UI work can move faster, but any business logic behind it should still be tested

## For Receipt Uploads and Files

* Users should be able to upload receipt files when needed
* Supported file types should include JPG, PNG, and PDF
* Receipt files should be stored in Google Cloud Storage in production
* The database should store file references and metadata, not raw file data
* Be careful with uploaded files because they may contain sensitive financial information
* Test important receipt behavior, especially file validation and model relationships

## Technology Preferences

* We prefer to use:

  * SQLite for local development
  * PostgreSQL for production
  * Django as the Python web framework
  * Django Templates for the frontend
  * Google Cloud Platform for hosting
  * Google Cloud Storage for file storage

* Vue.js or Nuxt will not be used in the MVP

* Keep the MVP simple and server-rendered with Django

* Avoid adding unnecessary frontend complexity

## Preferred Development Flow

* Red: write a failing test first
* Green: write the simplest code that makes the test pass
* Refactor: improve the code while keeping tests passing
* Keep each change small and understandable
* Explain each code change clearly
* Run tests often
* Do not move to the next feature while important tests are failing

## Definition of Done

A feature is done only when:

* The expected behavior is covered by tests where appropriate
* The tests pass
* The code is simple and readable
* The code change is explained clearly
* Important financial calculations are correct
* Transfers are handled separately from income and expenses
* The UI works end-to-end when the feature has a UI part
* Existing working behavior has not been broken
* No unnecessary technology has been added

## Final Priority

Correct financial behavior is the highest priority.

Clean code, test-first development, and clear explanations are not optional extras.

They are part of the way this project should be built.
