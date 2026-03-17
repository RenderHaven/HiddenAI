class InputController:

    def __init__(self, overlay):
        self.overlay = overlay
        self.events = {}   # dynamic event registry

    # -------------------------
    # REGISTER NEW EVENT
    # -------------------------
    def add_event(self, key, callback, modifier=None):
        """
        key: Qt.Key
        callback: function(app, event)
        modifier: Qt.KeyboardModifier or None
        """
        self.events[(key, modifier)] = callback

    # -------------------------
    # HANDLE KEY EVENT
    # -------------------------
    def handle(self, event):

        key = event.key()
        mod = event.modifiers()

        # dynamic lookup
        if (key, mod) in self.events:
            self.events[(key, mod)](self.overlay, event)
            

        if (key, None) in self.events:
            self.events[(key, None)](self.overlay, event)
            

        self._default_text_input(event)
        
    def _default_text_input(self, event):
            store = self.overlay.app.store
            o = self.overlay

            text = event.text()

            if text.isprintable():
                store.current_text += text

            o.update()

    # -------------------------
    # KEY RELEASE
    # -------------------------
    def release(self, event):

        key = event.key()
        mod = event.modifiers()

        if (key, mod) in self.events:
            self.events[(key, mod)](self.overlay, event)
