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

    VALIDATION
      "ows_url" "(\b(https?|ftp|file)://)?[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]"
    END
    METADATA
        'ows_onlineresource'         "%ows_url%"
        'ows_title'                 '{title}'
        'ows_abstract'              '{abstract}'
        'ows_extent'                '{extent}'
        'ows_srs'                   '{projection} {projections}'
        'ows_metadataurl_type'      'TC211'
        'ows_metadataurl_format'    'application/xml'
        'ows_metadataurl_href'      '{mdurl}'
        'wms_include_items'         'all'
        'gml_include_items'         'all'
    END
    {classes}
END