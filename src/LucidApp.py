"""
wat-this (formerly Lucid) - Backward Compatibility Forwarder.
Runs wat_this.py directly.
"""
import sys
import os

if __name__ == "__main__":
    import wat_this

    app = wat_this.WatThisApp()
    app.run()