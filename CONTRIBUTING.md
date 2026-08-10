# Contributing to Qucoon AI Projects

Thank you for your interest in contributing to our AI/ML projects! This guide will help you understand our contribution process and standards.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. By participating in this project, you agree to abide by our code of conduct:

- **Be respectful** and considerate in all interactions
- **Be collaborative** and help others learn and grow
- **Be inclusive** and welcome diverse perspectives
- **Be constructive** when providing feedback
- **Be professional** in all communications

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **Bug fixes** - Fix issues in existing code
- **Feature development** - Add new functionality
- **Model improvements** - Enhance model performance or architecture
- **Documentation** - Improve or add documentation
- **Testing** - Add or improve test coverage
- **Code quality** - Refactoring and optimization
- **Experiments** - Research and experimental work

### Getting Started

1. **Fork the repository** and clone your fork
2. **Set up your development environment** following the [onboarding guide](docs/ONBOARDING.md)
3. **Create a feature branch** from main
4. **Make your changes** following our coding standards
5. **Test your changes** thoroughly
6. **Submit a pull request** with a clear description

## Development Workflow

### 1. Setting Up Your Environment

```bash
# Clone your fork
git clone https://github.com/your-username/project-name.git
cd project-name

# Add upstream remote
git remote add upstream https://github.com/qucoon/project-name.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If available

# Install pre-commit hooks
pre-commit install
```

### 2. Creating a Feature Branch

```bash
# Sync with upstream
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for experiments
git checkout -b experiment/your-experiment-name
```

### 3. Making Changes

Follow our [coding standards](docs/CODING_STANDARDS.md):

- Write clear, documented code
- Add type hints to all functions
- Follow PEP 8 style guidelines
- Write comprehensive tests
- Update documentation as needed

### 4. Testing Your Changes

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run linting
flake8 src/ tests/

# Format code
black src/ tests/

# Type checking
mypy src/
```

### 5. Committing Changes

Follow our [commit message format](docs/GIT_WORKFLOW.md#commit-message-format):

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat(model): add transformer architecture for text classification"

# Push to your fork
git push origin feature/your-feature-name
```

## Pull Request Process

### Before Submitting

- [ ] **Code follows** our style guidelines
- [ ] **Tests pass** locally
- [ ] **Documentation updated** if needed
- [ ] **No merge conflicts** with main branch
- [ ] **Commit messages** follow our format
- [ ] **PR description** is clear and complete

### PR Description Template

Use our [PR template](.github/PULL_REQUEST_TEMPLATE.md) and include:

- **Clear description** of changes
- **Motivation** for the changes
- **Testing approach** used
- **Screenshots** if UI changes
- **Breaking changes** if any
- **Related issues** or experiments

### Review Process

1. **Automated checks** must pass (CI/CD pipeline)
2. **Code review** by at least one team member
3. **Address feedback** promptly and thoroughly
4. **Final approval** from maintainer
5. **Merge** using appropriate strategy

### Review Criteria

Reviewers will evaluate:

- **Correctness**: Does the code work as intended?
- **Performance**: Are there any performance implications?
- **Security**: Are there any security concerns?
- **Maintainability**: Is the code readable and well-structured?
- **Testing**: Is there adequate test coverage?
- **Documentation**: Is the code properly documented?

## Contribution Guidelines

### Code Quality Standards

#### Python Code
```python
# Good example
def train_model(
    X: np.ndarray, 
    y: np.ndarray,
    config: Dict[str, Any]
) -> Tuple[torch.nn.Module, Dict[str, float]]:
    """Train a machine learning model.
    
    Args:
        X: Training features with shape (n_samples, n_features).
        y: Training targets with shape (n_samples,).
        config: Training configuration parameters.
        
    Returns:
        Tuple of trained model and training metrics.
        
    Raises:
        ValueError: If input data is invalid.
    """
    # Validate inputs
    if X.shape[0] != y.shape[0]:
        raise ValueError("X and y must have same number of samples")
    
    # Implementation here
    model = create_model(config)
    metrics = fit_model(model, X, y, config)
    
    return model, metrics
```

#### Documentation
- All public functions must have docstrings
- Use Google-style docstrings
- Include examples for complex functions
- Update README for significant changes

#### Testing
```python
# Good test example
def test_train_model_with_valid_data():
    """Test model training with valid input data."""
    # Arrange
    X = np.random.rand(100, 10)
    y = np.random.randint(0, 2, 100)
    config = {"epochs": 5, "learning_rate": 0.01}
    
    # Act
    model, metrics = train_model(X, y, config)
    
    # Assert
    assert model is not None
    assert "accuracy" in metrics
    assert metrics["accuracy"] > 0.5
```

### ML-Specific Guidelines

#### Experiment Contributions
When contributing experiments:

1. **Document hypothesis** clearly
2. **Use consistent evaluation** metrics
3. **Track all experiments** with MLflow/W&B
4. **Compare with baselines** systematically
5. **Report negative results** too

#### Model Contributions
When contributing models:

1. **Provide model card** with performance metrics
2. **Include training scripts** and configurations
3. **Add inference examples**
4. **Document limitations** and biases
5. **Ensure reproducibility**

#### Data Contributions
When contributing data processing:

1. **Validate data quality**
2. **Document data sources**
3. **Handle privacy requirements**
4. **Provide data schemas**
5. **Include data tests**

## Communication Channels

### Getting Help
- **Team Chat**: #ai-team-help for questions
- **GitHub Issues**: For bug reports and feature requests
- **Team Meetings**: Weekly standup for discussions
- **Office Hours**: [Schedule] for one-on-one help

### Reporting Issues
When reporting bugs or issues:

1. **Search existing issues** first
2. **Use issue templates** provided
3. **Provide minimal reproduction** example
4. **Include environment details**
5. **Add relevant labels**

### Feature Requests
When requesting features:

1. **Describe the problem** you're solving
2. **Explain the proposed solution**
3. **Consider alternatives**
4. **Estimate impact and effort**
5. **Discuss with team** before implementation

## Recognition and Attribution

### Contributor Recognition
We recognize contributions through:

- **GitHub contributors** page
- **Release notes** acknowledgments
- **Team meetings** shout-outs
- **Internal presentations** credits

### Attribution Guidelines
- **Cite external work** properly
- **Credit collaborators** in commit messages
- **Acknowledge data sources**
- **Reference research papers** used

## Release Process

### Version Management
We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Contributions
To contribute to releases:

1. **Test release candidates** thoroughly
2. **Update documentation** for new features
3. **Write release notes** for your contributions
4. **Participate in release reviews**

## Best Practices for Contributors

### Development Tips
1. **Start small** - Make incremental changes
2. **Test early** - Write tests as you develop
3. **Document as you go** - Don't leave it for later
4. **Ask questions** - Better to clarify than assume
5. **Share progress** - Keep team informed

### Collaboration Tips
1. **Communicate clearly** in PRs and issues
2. **Be responsive** to feedback and questions
3. **Help others** when you can
4. **Share knowledge** through documentation
5. **Participate actively** in team discussions

### Learning and Growth
1. **Review others' code** to learn new techniques
2. **Attend team meetings** and presentations
3. **Read research papers** relevant to projects
4. **Experiment** with new approaches
5. **Share learnings** with the team

## Troubleshooting Common Issues

### Environment Issues
```bash
# Clear pip cache
pip cache purge

# Reinstall dependencies
pip uninstall -r requirements.txt -y
pip install -r requirements.txt

# Reset pre-commit
pre-commit clean
pre-commit install
```

### Git Issues
```bash
# Sync fork with upstream
git remote add upstream https://github.com/qucoon/project-name.git
git fetch upstream
git checkout main
git merge upstream/main

# Resolve merge conflicts
git status
# Edit conflicted files
git add .
git commit -m "resolve merge conflicts"
```

### Testing Issues
```bash
# Run specific test
pytest tests/test_specific.py::test_function

# Run with verbose output
pytest -v tests/

# Run with debugging
pytest --pdb tests/
```

## Questions?

If you have questions about contributing:

1. **Check the documentation** first
2. **Search existing issues** and discussions
3. **Ask in team chat** #ai-team-help
4. **Create an issue** for complex questions
5. **Schedule office hours** for detailed discussions

Thank you for contributing to our AI projects! Your contributions help make our team and products better.