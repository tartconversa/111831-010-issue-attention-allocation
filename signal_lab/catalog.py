from .records import Source


class SourceCatalog:
    def __init__(self, sources=()):
        self._sources = {source.source_id: source for source in sources}

    def get(self, source_id):
        return self._sources.get(source_id)

    def active_sources(self, region=None):
        values = (source for source in self._sources.values() if source.active)
        if region is not None:
            values = (source for source in values if source.region == region)
        return tuple(sorted(values, key=lambda source: source.source_id))
