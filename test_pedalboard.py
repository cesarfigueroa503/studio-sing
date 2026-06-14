import pedalboard
try:
    print(dir(pedalboard))
    # pedalboard.io.AudioFile might exist
    import pedalboard.io
    print(dir(pedalboard.io))
except Exception as e:
    print(f"Error: {e}")
