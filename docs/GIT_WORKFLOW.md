# Git Workflow

This document outlines the Git workflow, branch management, and collaboration practices for AI/ML projects.

## Branch Naming Conventions

### Branch Types
- **feature/**: New features or enhancements
- **bugfix/**: Bug fixes
- **experiment/**: ML experiments and model iterations
- **hotfix/**: Critical production fixes
- **docs/**: Documentation updates
- **refactor/**: Code refactoring without functionality changes

### Naming Format
```
<type>/<ticket-id>-<short-description>
```

### Examples
```bash
feature/ML-123-transformer-model
bugfix/ML-456-data-loading-error
experiment/ML-789-bert-fine-tuning
hotfix/ML-101-memory-leak-fix
docs/ML-234-api-documentation
refactor/ML-567-model-architecture
```

## Commit Message Format

### Conventional Commits
We follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks
- **perf**: Performance improvements
- **exp**: Experiment-related changes

### Examples
```bash
feat(model): add transformer architecture for text classification

fix(data): resolve memory leak in data loader
- Fixed iterator not being properly closed
- Added context manager for file handling

exp(bert): fine-tune BERT on domain-specific data
- Achieved 0.92 F1 score on validation set
- Used learning rate 2e-5 with 3 epochs
- Saved model checkpoint to models/bert_v1.2.0

docs(api): update model inference documentation

test(utils): add unit tests for data preprocessing functions

chore(deps): update torch to version 2.0.1
```

## Pull Request Process

### Before Creating PR
1. **Sync with main branch**
   ```bash
   git checkout main
   git pull origin main
   git checkout feature/your-branch
   git rebase main
   ```

2. **Run quality checks**
   ```bash
   # Format code
   black src/ tests/
   
   # Run linting
   flake8 src/ tests/
   
   # Run tests
   pytest tests/
   
   # Type checking
   mypy src/
   ```

3. **Update documentation**
   - Update README if needed
   - Add/update docstrings
   - Update CHANGELOG.md

### PR Requirements
- [ ] **Descriptive title** following conventional commit format
- [ ] **Detailed description** explaining changes
- [ ] **Tests added/updated** for new functionality
- [ ] **Documentation updated** if applicable
- [ ] **No merge conflicts** with main branch
- [ ] **CI checks passing**
- [ ] **At least one reviewer** assigned

### PR Description Template
```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Model improvement (changes to model architecture, training, or performance)
- [ ] Documentation update
- [ ] Experiment (research or experimental changes)

## Testing Done
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Model performance validated

## Experiment Results (if applicable)
- **Baseline metrics**: [Previous performance]
- **New metrics**: [Current performance]
- **Improvement**: [Quantified improvement]
- **Validation method**: [How results were validated]

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Code is commented, particularly in hard-to-understand areas
- [ ] Corresponding changes to documentation made
- [ ] Changes generate no new warnings
- [ ] Tests added that prove fix is effective or feature works
- [ ] New and existing unit tests pass locally
- [ ] Dependent changes have been merged and published
```

## Code Review Guidelines

### For Authors
1. **Keep PRs small** (< 400 lines of code)
2. **Provide context** in PR description
3. **Respond promptly** to review feedback
4. **Test thoroughly** before requesting review
5. **Address all comments** before re-requesting review

### For Reviewers
1. **Review within 24 hours** of assignment
2. **Be constructive** and specific in feedback
3. **Focus on**:
   - Code correctness and logic
   - Performance implications
   - Security considerations
   - Maintainability
   - Test coverage
   - Documentation quality

### Review Checklist
- [ ] **Functionality**: Does the code do what it's supposed to do?
- [ ] **Performance**: Are there any performance bottlenecks?
- [ ] **Security**: Are there any security vulnerabilities?
- [ ] **Maintainability**: Is the code readable and well-structured?
- [ ] **Tests**: Are there adequate tests for the changes?
- [ ] **Documentation**: Is the code properly documented?
- [ ] **Standards**: Does the code follow our coding standards?

## Merge Strategies

### Merge Types
1. **Squash and merge** (preferred for feature branches)
   - Creates clean, linear history
   - Combines all commits into single commit
   - Use for completed features

2. **Rebase and merge** (for small, clean commits)
   - Preserves individual commits
   - Creates linear history
   - Use when commits are meaningful individually

3. **Merge commit** (for release branches)
   - Preserves branch history
   - Shows when features were integrated
   - Use for major releases or hotfixes

### When to Use Each Strategy
```bash
# Feature development (squash and merge)
feature/ML-123-new-model → main

# Bug fixes with multiple logical commits (rebase and merge)
bugfix/ML-456-data-pipeline → main

# Release branches (merge commit)
release/v1.2.0 → main
```

## Experiment Workflow

### Experiment Branches
```bash
# Create experiment branch
git checkout -b experiment/ML-789-bert-variants

# Make experimental changes
git add .
git commit -m "exp(bert): try different learning rates"

# Track experiment results in commit messages
git commit -m "exp(bert): lr=1e-5 achieves 0.89 F1 score

Results:
- Training loss: 0.23
- Validation loss: 0.31
- F1 score: 0.89
- Training time: 2.5 hours"
```

### Experiment Documentation
Create experiment log in commit messages:
```bash
git commit -m "exp(model): compare transformer architectures

Tested architectures:
1. BERT-base: F1=0.87, Time=1.2h
2. RoBERTa-base: F1=0.89, Time=1.5h  
3. DistilBERT: F1=0.85, Time=0.8h

Best: RoBERTa-base for accuracy
Best: DistilBERT for speed

Next: Try RoBERTa-large"
```

## Release Management

### Version Numbering
Follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Process
1. **Create release branch**
   ```bash
   git checkout -b release/v1.2.0
   ```

2. **Update version numbers**
   - Update `__version__` in `src/__init__.py`
   - Update `pyproject.toml`
   - Update `CHANGELOG.md`

3. **Final testing**
   ```bash
   pytest tests/
   python -m src.validate_release
   ```

4. **Create release PR**
   ```bash
   git push origin release/v1.2.0
   # Create PR: release/v1.2.0 → main
   ```

5. **Tag release**
   ```bash
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   ```

## Hotfix Workflow

### Critical Bug Fixes
```bash
# Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/ML-999-critical-bug

# Make minimal fix
git add .
git commit -m "fix(critical): resolve memory leak in inference"

# Create PR for immediate merge
git push origin hotfix/ML-999-critical-bug
```

### Hotfix Requirements
- **Minimal changes** only
- **Immediate review** required
- **Fast-track merge** process
- **Immediate deployment** consideration

## Best Practices

### Daily Workflow
```bash
# Start of day: sync with main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/ML-123-new-feature

# Work and commit frequently
git add .
git commit -m "feat(model): add initial model structure"

# Push regularly
git push origin feature/ML-123-new-feature

# End of day: push all work
git push origin feature/ML-123-new-feature
```

### Commit Best Practices
1. **Commit frequently** with logical chunks
2. **Write clear messages** explaining why, not what
3. **Keep commits atomic** (one logical change per commit)
4. **Test before committing**
5. **Don't commit sensitive data**

### Branch Management
1. **Delete merged branches** to keep repository clean
2. **Keep branches up-to-date** with main
3. **Use descriptive names** for branches
4. **Limit long-running branches**

### Collaboration Tips
1. **Communicate changes** that affect others
2. **Coordinate on shared files** to avoid conflicts
3. **Use draft PRs** for work-in-progress
4. **Tag team members** for relevant reviews
5. **Update issue trackers** with progress