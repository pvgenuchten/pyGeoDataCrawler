LAYER
    NAME    '{name}'
    TYPE    {type}
    DATA    '{path}'
    PROJECTION
        'init={projection}'
    END
    EXTENT {extent}
    STATUS on
    Template '{template}'
    METADATA
        'ows_title'                 '{title}'
        'ows_abstract'                 '{abstract}'
        'ows_extent'                '{extent}'
        'ows_srs'                   '{projection} {projections}'
        'ows_metadataurl_type'      'TC211'
        'ows_metadataurl_format'    'application/xml'
        'ows_metadataurl_href'      '{mdurl}'
    END
    {classes}
END