# Contributing to DeepSigma

Thank you for your interest in contributing to DeepSigma! This document provides guidelines and information for contributors.

## Getting Started

1. **Fork the repository** and clone your fork locally
2. 2. **Install dependencies**: `pip install -r requirements.txt`
   3. 3. **Run the existing examples**: `python run_supervised.py` to see the supervision loop in action
      4. 4. **Read the wiki**: The [DeepSigma Wiki](https://github.com/8ryanWh1t3/DeepSigma/wiki) has detailed documentation on architecture, concepts, and schemas
        
         5. ## Development Setup
        
         6. ```bash
            # Clone your fork
            git clone https://github.com/<your-username>/DeepSigma.git
            cd DeepSigma

            # Create a virtual environment
            python -m venv venv
            source venv/bin/activate  # or `venv\Scripts\activate` on Windows

            # Install dependencies
            pip install -r requirements.txt

            # Run the supervisor
            python run_supervised.py

            # Validate example artifacts against schemas
            python validate_examples.py
            ```

            ## Project Structure

            ```
            DeepSigma/
            ├── run_supervised.py          # Main supervision entry point
            ├── degrade_ladder.py          # Degrade ladder logic
            ├── supervisor_scaffold.py     # Supervisor engine scaffold
            ├── policy_loader.py           # Policy pack loader
            ├── invariant_check.py         # Invariant verification
            ├── read_after_write.py        # Read-after-write verifier
            ├── replay_episode.py          # Episode replay harness
            ├── validate_examples.py       # Schema validation for examples
            ├── mcp_server_scaffold.py     # MCP server scaffold
            ├── schemas/                   # JSON Schemas
            ├── examples/                  # Example artifacts
            ├── adapters/                  # Integration adapters
            ├── dashboard/                 # React monitoring dashboard
            └── tests/                     # Test suite (in progress)
            ```

            ## How to Contribute

            ### Find an Issue

            Browse the [open issues](https://github.com/8ryanWh1t3/DeepSigma/issues) to find something to work on. Issues labeled `good first issue` are great starting points for new contributors.

            Issues are organized into two milestones:

            - **v0.2 — Schema Compliance & Testing**: Foundation work (schema fixes, tests, CI)
            - - **v0.3 — Adapters & Integrations**: Adapter implementations and tooling
             
              - ### Making Changes
             
              - 1. Create a feature branch from `main`: `git checkout -b feature/your-feature-name`
                2. 2. Make your changes, following the coding standards below
                   3. 3. Validate your changes against the JSON schemas: `python validate_examples.py`
                      4. 4. Run tests (once available): `pytest tests/`
                         5. 5. Commit with a descriptive message referencing the issue: `git commit -m "Fix episode schema compliance (closes #1)"`
                            6. 6. Push to your fork and open a Pull Request
                              
                               7. ### Coding Standards
                              
                               8. - **Python**: Follow PEP 8. Use type hints where practical.
                                  - - **JSON Schemas**: All artifact outputs must conform to their respective schemas in `schemas/`.
                                    - - **Naming**: Use snake_case for Python files and functions, camelCase for JSON schema properties.
                                      - - **Documentation**: Update wiki pages and docstrings when changing behavior.
                                       
                                        - ### Schema Compliance
                                       
                                        - DeepSigma is a schema-driven framework. All artifacts (episodes, drift events, action contracts, DTE packs, policy packs) must conform to their JSON schemas. Before submitting a PR:
                                       
                                        - 1. Run `python validate_examples.py` to check all example artifacts
                                          2. 2. If you modify a schema, ensure all existing examples still validate
                                             3. 3. If you add a new artifact type, add matching examples and schema validation
                                               
                                                4. ### Commit Messages
                                               
                                                5. Use clear, descriptive commit messages:
                                               
                                                6. - `Fix: <description>` for bug fixes
                                                   - - `Add: <description>` for new features
                                                     - - `Docs: <description>` for documentation changes
                                                       - - `Test: <description>` for test additions
                                                         - - Reference issues with `#N` or `closes #N`
                                                          
                                                           - ## Pull Request Process
                                                          
                                                           - 1. Ensure your PR targets the `main` branch
                                                             2. 2. Fill out the PR description explaining what changed and why
                                                                3. 3. Reference the related issue(s)
                                                                   4. 4. Ensure all schema validations pass
                                                                      5. 5. Respond to review feedback promptly
                                                                        
                                                                         6. ## Reporting Bugs
                                                                        
                                                                         7. If you find a bug, please [open an issue](https://github.com/8ryanWh1t3/DeepSigma/issues/new) with:
                                                                        
                                                                         8. - A clear title and description
                                                                            - - Steps to reproduce the issue
                                                                              - - Expected vs. actual behavior
                                                                                - - Any relevant log output or error messages
                                                                                 
                                                                                  - ## Questions?
                                                                                 
                                                                                  - Check the [FAQ](https://github.com/8ryanWh1t3/DeepSigma/wiki/FAQ) on the wiki, or open a [Discussion](https://github.com/8ryanWh1t3/DeepSigma/discussions) for questions that aren't bug reports or feature requests.
