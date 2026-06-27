def test_micro_brain_package_imports():
    import ai.micro_brain.brain as brain_pkg
    import ai.micro_brain.main as main_mod

    assert hasattr(brain_pkg, "NeuralBrain")
    assert hasattr(main_mod, "MicroNeuralBrain")
