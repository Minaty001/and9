def test_micro_brain_package_imports():
    import micro_brain.brain as brain_pkg
    import micro_brain.main as main_mod

    assert hasattr(brain_pkg, "NeuralBrain")
    assert hasattr(main_mod, "MicroNeuralBrain")
