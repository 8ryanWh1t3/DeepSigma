import pytest
from deepsigma_cartography.sample import AS_OF, sample_atlas

@pytest.fixture
def atlas():
    return sample_atlas()

@pytest.fixture
def view(atlas):
    return atlas.view(as_of=AS_OF)
