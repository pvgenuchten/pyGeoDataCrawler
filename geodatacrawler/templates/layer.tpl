LAYER
    NAME    '{name}'
    TYPE    {type}
    CONNECTIONTYPE {connectiontype}
    CONNECTION  "{connection}"
    DATA "{data}"
    PROJECTION
        '{projection}'
    END
    EXTENT '{extent}'
    STATUS on
    PROCESSING 'CLOSE_CONNECTION=DEFER'
    Template '{template}'

    METADATA
        'ows_title'                 {title}
        'ows_abstract'              {abstract}
        'ows_extent'                '{extent}'
        'ows_srs'                   '{projections}'
        'ows_metadataurl_type'      'TC211'
        'ows_metadataurl_format'    'application/xml'
        'ows_metadataurl_href'      '{mdurl}'
        'wms_include_items'         'all'
        'gml_include_items'         'all'
        'gml_featureid'             '{id}'
        'wcs_label'                 'WCS'
        'wcs_rangeset_name'         '{name}'
        'wcs_rangeset_label'        {title}
    END
    {classes}
END