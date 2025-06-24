# creates a mapfile from index

from importlib.resources import path
from copy import deepcopy
from decimal import *
import mappyfile, click, yaml
import os, time, sys, re, math, glob
import pprint
import urllib.request
from geodatacrawler.utils import indexFile, dict_merge
from geodatacrawler.metadata import load_default_metadata, merge_folder_metadata
from geodatacrawler import GDCCONFIG
from yaml.loader import SafeLoader
import importlib.resources as pkg_resources
from urllib.parse import urlparse
from . import templates
from pathlib import Path

@click.command()
@click.option('--dir', nargs=1, type=click.Path(exists=True),
              required=True, help="Directory as source for mapfile")
@click.option('--dir-out', nargs=1, type=click.Path(exists=True),
              required=False, help="Directory as target for the generated mapfiles")
@click.option('--dir-out-mode', nargs=1, required=False, help="flat|nested indicates if files in output folder are nested")
@click.option('--recursive', nargs=1, required=False, help="False|True, should script recurse into subfolders")
def mapForDir(dir, dir_out, dir_out_mode, recursive):
    if not dir:
        dir = "."
    if not dir_out:
        dir_out = dir
    if not dir_out_mode or dir_out_mode not in ["flat","nested"]:
        dir_out_mode = "flat"
    if recursive and recursive.lower()=='true':
        recursive = True
    else:
        recursive = False
    print(f'Creating a mapfile for dir {dir} to {dir_out} as {dir_out_mode}, recursive: {recursive}')

    # initial config (from program folder)
    config = initialConfig(dir,dir_out)
    processPath("", config, dir_out, dir_out_mode, recursive)

def initialConfig(dir,dir_out):    
    # core metadata gets populated by merging the index.yaml content from parent folders
    initialMetadata = load_default_metadata("update")
    config = initialMetadata.get('robot',{})
    config['rootDir'] = dir   
    config['outDir'] = os.getenv('pgdc_dir_out') or dir_out
    config['mdUrlPattern'] = os.getenv('pgdc_md_url') or ''
    config['msUrl'] = os.getenv('pgdc_ms_url') or ''
    config['webdavUrl'] = os.getenv('pgdc_webdav_url') or ''
    config['mdLinkTypes'] = os.getenv('pgdc_md_link_types') or ['OGC:WMS','OGC:WFS','OGC:WCS']
    # default styling
    config['map'] = {"styles":[{"classes":"#56a1b3,#80bfab,#abdda4,#c7e8ad,#e3f4b6,#ffffbf,#fee4a0,#fec980,#fdae61,#f07c4a,#e44b33,#d7191c".split(',')}]}
    config['map']['extent'] = [None,None,None,None]
    initialMetadata['robot'] = config
    return initialMetadata

def processPath(relPath, parentMetadata, dir_out, dir_out_mode, recursive):

    parentConfig = parentMetadata.get('robot',{})    
    # merge folder metadata
    coreMetadata = merge_folder_metadata(parentMetadata, os.path.join(parentConfig['rootDir'],relPath), "update")
  
    config = coreMetadata.get('robot',{})

    skipSubfolders = False
    if 'skip-subfolders' in config:
        skipSubfolders = config['skip-subfolders']

    # initalise folder mapfile
    tpl = pkg_resources.open_text(templates, 'default.map')
    mf = mappyfile.load(tpl)
    lyrs = mf['layers']

    # set up header
    mf["name"] = list(filter(None, str(os.path.abspath(config['rootDir']) + os.sep + relPath).split(os.sep))).pop()
    mf["web"]["metadata"]["ows_title"] = (coreMetadata.get('identification',{}).get("title") or "map").replace('\r','').replace('\n','').replace("'","")
    mf["web"]["metadata"]["ows_abstract"] = (coreMetadata.get('identification',{}).get("abstract", "") or "").replace('\r','').replace('\n','').replace("'","")
    kw = []
    for k,v in coreMetadata.get('identification',{}).get('keywords',{}).items():
            if v.get('keywords') and len(v.get('keywords')) > 0 :
                if isinstance(v.get('keywords'), list):
                    kw += v.get('keywords')
                else: #string
                    kw.append(v.get('keywords'))
    mf["web"]["metadata"]["ows_keywordlist"] = ','.join(kw)
    # todo: by thesaurus
    # wms_keywordlist_vocabulary
    # wms_keywordlist_[vocabulary’s name]_items

    # todo: wms_identifier_authority, wms_identifier_value
    # wms_authorityurl_name, wms_authorityurl_href

    # takes the first contact (maybe override from robot-section)
    if coreMetadata.get('contact') is not None and len(coreMetadata['contact'].keys()) > 0:
        mf["web"]["metadata"]["ows_role"] = list(coreMetadata.get('contact').keys())[0]
        first = coreMetadata.get('contact')[mf["web"]["metadata"]["ows_role"]]
        mf["web"]["metadata"]["ows_address"] = first.get("address","")
        mf["web"]["metadata"]["ows_city"] = first.get("city","")
        mf["web"]["metadata"]["ows_stateorprovince"] = first.get("administrativearea","")
        mf["web"]["metadata"]["ows_postcode"] = first.get("postalcode","")   
        mf["web"]["metadata"]["ows_country"] = first.get("country","")         
        mf["web"]["metadata"]["ows_contactelectronicmailaddress"] = first.get("email","")
        mf["web"]["metadata"]["ows_contactperson"] = first.get("individualname","")
        mf["web"]["metadata"]["ows_contactorganization"] = first.get("organization","")
        mf["web"]["metadata"]["ows_contactposition"] = first.get("positionname","")
        mf["web"]["metadata"]["ows_contactvoicetelephone"] = first.get("phone","")
        mf["web"]["metadata"]["ows_attribution_onlineresource"] = first.get("url","")
    mf["web"]["metadata"]["ows_fees"] = coreMetadata.get('identification').get("fees","")
    mf["web"]["metadata"]["ows_accessconstraints"] = coreMetadata.get('identification').get("accessconstraints","") 
    mf["web"]["metadata"]["ows_onlineresource"] = config['msUrl'] + mf["name"]
    mf["web"]["metadata"]["oga_onlineresource"] = mf["web"]["metadata"]["ows_onlineresource"] + '/ogcapi'

    filelist = glob.glob(os.path.join(config['rootDir'],relPath)+os.sep+'*')
    for file in sorted(filelist): 
        fname = str(file).split(os.sep).pop()
        if os.path.isdir(str(file)) and recursive and not fname.startswith('.'):
            if skipSubfolders:
                print('Skip path: '+ str(file))
            else:
                # go one level deeper
                print('Process path: '+ str(file))
                processPath(os.path.join(relPath,fname), deepcopy(coreMetadata), dir_out, dir_out_mode, recursive)
        else:
            if 'skip-files' in config and config['skip-files'] != '' and re.search(config['skip-files'], fname):
                print('Skip file',fname)
            # process the file
            elif '.' in str(file):
                base, extension = str(file).rsplit('.', 1)
                fn = base.split(os.sep).pop()

                # do we trigger on ymls only, or also on spatial files? --> No 
                # to go back to the file from the yml works via name matching or distribution(s)?
                if extension.lower() in ["yml","yaml"] and fn != "index":
                    # todo: operational metadata contains information on how to process the folder
                    
                    # process the layer
                    #try:
                    if os.path.exists(str(file)):
                        with open(str(file), mode="r", encoding="utf-8") as f:
                            cnf = yaml.load(f, Loader=SafeLoader)
                            cnt = deepcopy(coreMetadata)
                            dict_merge(cnt,cnf)

                            ly = cnt.get('robot',{}).get('map',{})
                            # prepare layer(s)
                            # print('Found',len(cnt.get('distribution',{}).items()),'existing disributions in',fname)

                            dataFile = []
                            # check if a data file with same name exits
                            for ext in GDCCONFIG["INDEX_FILE_TYPES"]:
                                if (os.path.exists(str(file).replace('yml',ext))):
                                    dataFile.append(str(file).replace('yml',ext))
                            
                            if len(dataFile) == 0:
                                for d,v in cnt.get('distribution',{}).items():
                                    # for each link check if local file exists
                                    parsed = urlparse(v.get('url',''))
                                    fn = str(parsed.path).split('/').pop()
                                    sf = os.path.join(config['rootDir'], relPath , fn)
                                    if v.get('type') in [None,'']:
                                        v['type'] = "unknown"
                                    if not v.get('type','').startswith('OGC:') and os.path.exists(sf):
                                        fb,e = str(fn).rsplit('.', 1)
                                        if e and e.lower() in GDCCONFIG["SPATIAL_FILE_TYPES"] and sf not in dataFile:
                                            dataFile.append(sf)

                            lyr = {}
                            # process the files in dataFile
                            for sf in dataFile:
                                print('processing file' + sf)
                                fn = sf.split('/').pop()
                                fb,e = fn.rsplit('.', 1) 
                                fileinfo = indexFile(sf, e)
                                if (fileinfo.get('spatial',{}).get('datatype','') == "grid"):
                                    lyr['type'] = 'grid'
                                elif (fileinfo.get('spatial',{}).get('geomtype','') == "curve"):
                                    lyr['type'] = 'line'
                                elif (fileinfo.get('spatial',{}).get('geomtype','') == "point"):  # table is suggested for CSV, which is usually point (or none)
                                    lyr['type'] = 'point'
                                else:
                                    lyr['type'] = 'polygon'
                                # check if a SLD exists
                                sld = None
                                if (os.path.exists(str(file).replace('yml','sld'))):
                                    sld = str(file).replace('yml','sld')
                                # initial
                                lyr['wgs84_bounds'] = [-180,-90,180,90] 
                                lyr['bounds'] = None
                                lyr['crs'] = 'epsg:4326' 

                                # object has 1 bounds in 4326 and may have one in original projection
                                for extent in fileinfo.get('identification',{}).get('extents',{}).get('spatial',[]):

                                    if '4326' in str(extent.get('crs','')) and len(extent.get('bbox',[])) == 4:
                                        updateBounds(extent.get('bbox'), config['map']['extent'])
                                        lyr['wgs84_bounds'] = extent.get('bbox')
                                    elif extent.get('crs') not in [None,''] and len(extent.get('bbox')) == 4:
                                        lyr['crs'] = extent.get('crs')
                                        lyr['bounds'] = extent.get('bbox')

                                # default val from index.yml
                                projections = ly.get('projections', 'epsg:4326 epsg:3857');
                                # first take value from file, take srs-str, else take override value from index.yml, else  4326
                                # else cnt['crs'] = cnt.get('identification').get('extents',{}).get('spatial',[{}])[0].get('crs')
                                if lyr['crs'] != 'epsg:4326' :
                                    projections = lyr['crs']  + ' ' + projections
                                else: 
                                    lyr['crs'] = 'epsg:4326'
                                    lyr['bounds'] = lyr['wgs84_bounds']

                                # evaluate if a custom style is defined
                                band1 = fileinfo.get('content_info',{}).get('dimensions',[{}])[0]
                                new_class_string2 = ""

                                if sld: # reference sld file in current folder
                                    new_class_string2 += f"STYLEITEM: \"sld://{os.path.join('' if dir_out_mode == 'nested' else relPath,sld)}\"\n"
                                elif 'styles' in ly.keys() and isinstance(ly['styles'],list):
                                    for style_reference in ly.get("styles", []): 
                                        # if isinstance(style_reference,dict): 
                                        #    new_class_string2 += f"CLASSGROUP \"{style_reference.get('name','Default')}\"\n"
                                        if isinstance(style_reference,str): # case string (mapfile syntax)
                                            stylefile = os.path.join(config['rootDir'],relPath,style_reference)
                                            if os.path.exists(stylefile):
                                                with open(stylefile) as f1:
                                                    new_class_string2 += f1.read()
                                            else:
                                                print(f'Stylefile {stylefile} does not exist')
                                        
                                        elif lyr['type']=='grid': # set colors for range, only first band supported
                                            new_class_string2 += colorCoding('grid',band1.get('min',0), band1.get('max',0),style_reference)
                                        else: # vector
                                            new_class_string2 += colorCoding(fileinfo.get('spatial',{}).get('geomtype',''),None,None,style_reference)
                                else:
                                    print(f'styles defined for layer {fn}, but not type list')
                                    
                                if new_class_string2 == "":
                                    new_class_string2 = pkg_resources.read_text(templates, 'class-' + lyr['type'] + '.tpl')

                                if 'template' not in ly.keys() or ly['template'] != '': # custom template
                                    if lyr['type']=='grid':
                                        ly['template'] = 'grid.html'
                                        if not os.path.exists(os.path.join(dir_out,(relPath if dir_out_mode == 'nested' else ''),'grid.html')):
                                            gridinfofile = pkg_resources.read_text(templates, 'grid.html')
                                            with open(os.path.join(dir_out,(relPath if dir_out_mode == 'nested' else ''),'grid.html'), 'w') as f:
                                                f.write(gridinfofile) 
                                    else:
                                        ly['template'] = ly.get('template', f'{fb}.html')
                                        vectorinfofile = "<!-- MapServer Template -->\n"
                                        for attr in (fileinfo.get('content_info',{}).get('attributes',[]) or []):
                                            vectorinfofile += f"{attr.get('title',attr['name'])}: [{attr['name']}] {attr.get('unit','')}<br/>\n"
                                        vectorinfofile += "<hr/>"
                                        with open(os.path.join(dir_out,(relPath if dir_out_mode == 'nested' else ''),fb+'.html'), 'w') as f:
                                            f.write(vectorinfofile) 

                                # prepend nodata on grids
                                if lyr['type']=='grid' and str(band1.get('nodata','')) not in ['None','','NaN']:
                                    new_class_string2 = 'PROCESSING "NODATA=' + str(band1.get('nodata', '')) + '"\n' + new_class_string2

                                new_layer_string = pkg_resources.read_text(templates, 'layer.tpl')

                                strLr = new_layer_string.format(name=fb,
                                    title='"'+str(cnt.get('identification',{}).get('title', '')).replace('\r','').replace('\n','').replace("'","")+'"',
                                    abstract='"'+str(cnt.get('identification',{}).get('abstract', '')).replace('\r','').replace('\n','').replace("'","")+'"',
                                    type=('raster' if lyr['type']=='grid' else lyr['type']),
                                    path=os.path.join('' if dir_out_mode == 'nested' else relPath,fn), # nested or flat
                                    template=ly.get('template'),
                                    projection=lyr['crs'],
                                    projections=projections,
                                    extent=" ".join(map(str,lyr['bounds'])),
                                    id="fid", # todo, use field from attributes, config?
                                    mdurl=config['mdUrlPattern'].format(cnt.get('metadata',{}).get('identifier',fb)) if config['mdUrlPattern'] != '' else '', # or use the externalid here (doi)
                                    classes=new_class_string2)
                                #except Exception as e:
                                #    print("Failed creation of layer {0}; {1}".format(cnt['name'], e))
                                    
                                try:
                                    mslr = mappyfile.loads(strLr)
                                    lyrs.insert(len(lyrs) + 1, mslr)
                                except Exception as e:
                                    print("Failed creation of layer {0}; {1}".format(fb, e))

                                # does metadata already include a link to wms/wfs? else add it.
                                for mdlinktype in config['mdLinkTypes']:
                                    relPath2 = relPath if dir_out_mode == 'nested' else ''
                                    if mdlinktype in ['OGC:WMS']:
                                        if not checkLink(cnt, mdlinktype, config):
                                            addLink(mdlinktype, fb, file, relPath2, mf['name'], config)
                                    elif fileinfo.get('spatial',{}).get('datatype','').lower() == 'grid' and mdlinktype == 'OGC:WCS':
                                        if not checkLink(cnt, mdlinktype, config):
                                            addLink(mdlinktype, fb, file, relPath2, mf['name'], config)
                                    elif fileinfo.get('spatial',{}).get('datatype','').lower() == 'vector' and mdlinktype == 'OGC:WFS' :
                                        if not checkLink(cnt, mdlinktype, config):
                                            addLink(mdlinktype, fb, file, relPath2, mf['name'], config)

    # map should have initial layer, remove it
    lyrs.pop(0)

    # print(mappyfile.dumps(mf))
    # write to parent folder as {folder}.map
    if len(lyrs) > 0: # do not create mapfile if no layers
        do = os.path.join(dir_out,(relPath if dir_out_mode == 'nested' else ''))
        mapfile =  os.path.join(do,mf['name'] + ".map")
        
        # check if folder exists
        if not os.path.exists(do):
            print('create folder',do)
            os.makedirs(do)

        mf['extent'] = " ".join(str(x) for x in config['map']['extent'])

        print(f'writing mapfile {mapfile}')
        mappyfile.save(mf, mapfile, 
            indent=4, spacer=' ', quote="'", newlinechar='\n',
            end_comment=False, align_values=False)
    else:
        print('Folder ' + os.path.join(config['rootDir'],relPath) + ' empty, skip creation')

'''
Verify if this metadata already has a link to this service
'''
def checkLink(md, type, config):
    if 'distribution' in md and md['distribution']:
        for k,v in md.get('distribution').items():
            if v.get('type','').upper() == type and v.get('url','').startswith(config['msUrl']):
                return True
    return False
 
'''
Append a link to this service
'''
def addLink(type, layer, file, relPath, map, config):
    print(f'Add link {type} to {str(file)}')
    # read file
    with open(str(file), mode="r", encoding="utf-8") as f:
        orig = yaml.load(f, Loader=SafeLoader)
    # add link
        if 'distribution' not in orig.keys() or orig['distribution'] is None:
            orig['distribution'] = {}
        msUrl2 = config['msUrl'] + (relPath if relPath != '' else '')
        orig['distribution'][type.split(':').pop()] = {
            'url':  msUrl2 + map +'?service='+type.split(':').pop()+'&amp;request=GetCapabilities',
            'type': type,
            'name': layer,
            'description': ''
        } 
    # write file
    with open(str(file), 'w') as f:
        yaml.dump(orig, f, sort_keys=False)

'''
sets a color coding for a layer
3 style configuration options:
    styles:
      - name: color
        classes: ['#56a1b3','#80bfab','#abdda4']
      - name: ranges
        classes: [
         {min: 0,max: 2,label: '0-2',color: '#56a1b3'},
         {min: 2,max: 4,label: '2-4',color: '#80bfab'},
         {min: 4,max: 6,label: '4-6',color: '#abdda4'}]
      - name: absolute
        classes: [
            { val: 0,label: 'false',color: '#56a1b3'},
            { val: 1,label: 'true', color: '#80bfab'}]
'''
def colorCoding(geomtype,min,max,style):

    if geomtype=='grid':
        prop = 'pixel'
    else: #vector
        prop = style.get('property')
        if prop in [None,'']:
            if 'classes' in style and len(style['classes']) > 0: # have single color style
                lbl = 'default'
                if isinstance(style['classes'][0],dict):
                    lbl = style['classes'][0].get('label',style.get('name','default'))
                return f"CLASS\nNAME '{lbl}'\nSTYLE\n{msStyler(geomtype,style['classes'][0])}\nEND\nEND\n\n"
            else:     
                return "" # No property for expression, use default color, 

    if isinstance(style,list):
        return colorCoding(geomtype,min,max,{"classes":style}) # backwards compat
    elif isinstance(style,dict): # 3 cases: array of color, array of ranges, array of absolutes
        classes = style.get('classes','#ff0000,#ffff00,#00ff00,#00ffff,#0000ff')
        clsstr = ""
        # test is classes is string -> array
        if isinstance(classes,str):
            classes = classes.split(',')
        # a list of classes
        if isinstance(classes[0],str) or isinstance(classes[0],list): # list may be a color [255 255 0]
            getcontext().prec = 4 # set precision of decimals, so classes are not too specific
            if min in [None,''] or max in [None,'']: # for vector max-min currently None, todo: can fetch from data
                rng = 0
            else:
                rng = Decimal(max - min)
            if rng > 0:
                sgmt =  Decimal(rng/len(classes))
                cur =  Decimal(min)
                for cls in classes:
                    clsstr += f"CLASS\nNAME '{cur} - {cur+sgmt}'\nGROUP '{style.get('name','Default')}'\nEXPRESSION ( [{prop}] >= {cur} AND [{prop}] <= {cur+sgmt} )\nSTYLE\n{msStyler(geomtype,cls)}\nEND\nEND\n\n"
                    cur += sgmt
                return clsstr
            elif rng == 0: # single value grid?
                return f"CLASS\nNAME '{min}'\nGROUP '{style.get('name','Default')}'\nEXPRESSION ( [{prop}] = {min} )\nSTYLE\n{msStyler(geomtype,classes[0])}\nEND\nEND\n\n"
            else:
                print('Can not derive classes, negative range',min,max,rng)
                return ""
        elif isinstance(classes[0],dict):
            for cls in classes:
                if 'val' in cls.keys() and cls['val'] not in [None]:
                    lbl = cls.get('label',str(cls['val']))
                    clsstr += f"CLASS\nNAME \"{lbl}\"\nGROUP \"{style.get('name','Default')}\"\nEXPRESSION ( [{prop}] = {quoteStr(cls['val'])} )\nSTYLE\n{msStyler(geomtype,cls)}\nEND\nEND\n\n"
                elif 'min' in cls.keys() and 'max' in cls.keys():
                    lbl = cls.get('label',(str(cls['min'])+' - '+str(cls['max'])))
                    clsstr += f"CLASS\nNAME \"{lbl}\"\nGROUP \"{style.get('name','Default')}\"\nEXPRESSION ( [{prop}] >= {cls['min']} AND [{prop}] <= {cls['max']} )\nSTYLE\n{msStyler(geomtype,cls)}\nEND\nEND\n\n"
            return clsstr
        else:
            print('type '+ str(type(classes[0])) +' not recognised for class') 
            return ""  
    else:
        print('type '+ str(type(style)) +' not recognised for style') 
        return ""
    

'''
codes a ms classes element
'''
def msStyler(geomtype,cls):
    if isinstance(cls,str) or isinstance(cls,list):
        cls = {'color': cls}
    color = hexcolor(cls.get('color','#eeeeee'))
    linecolor = hexcolor(cls.get('linecolor','#232323'))
    symbol = cls.get('symbol','circle')
    size = float(cls.get('size') or 5) 
    width = float(cls.get('width') or 0.1)
    if geomtype=='grid':
        return f'COLOR "{color}"\n'
    elif geomtype=='point':
      return f'SYMBOL "{symbol}"\nCOLOR "{color}"\nSIZE {str(size)}\nOUTLINECOLOR "{linecolor}"\nOUTLINEWIDTH 0.1\n'
    elif geomtype=='polyline':
        return f'WIDTH {str(width)}\nCOLOR "{color}"\nLINEJOIN "bevel"\n'
    elif geomtype=='polygon':
        return f'COLOR "{color}"\nOUTLINECOLOR "{linecolor}"\nOUTLINEWIDTH {str(width)}\n'
    else:
        print(f'unknown type when building class element: {geomtype}')


'''
if color is rgb, return as hex
'''
def hexcolor(clr):
    if clr in [None,'']:
        return "#CCCCCC"
    elif isinstance(clr,list):
        return '#{:02x}{:02x}{:02x}'.format(int(clr[0]),int(clr[1]),int(clr[2]))
    elif len(clr.split(' ')) == 3:
        return hexcolor(clr.split(' '))
    #elif len(clr) == 7 and clr.startswith('#'): # could check if starts with '#'
    #    return clr
    else: 
        return clr

'''
Extent a targetbox (tb) with a source box (sb)
'''
def updateBounds(sb,tb):
    if sb and len(sb) > 3:
        if not (sb[0] in [None,''] and math.isinf(float(sb[0]))) and (not tb[0] or float(sb[0]) < tb[0]):
            tb[0] = float(sb[0])
        if not (sb[1] in [None,''] and math.isinf(float(sb[1]))) and (not tb[1] or float(sb[1]) < tb[1]):
            tb[1] = float(sb[1])
        if not (sb[2] in [None,''] and math.isinf(float(sb[2]))) and (not tb[2] or float(sb[2]) > tb[2]):
            tb[2] = float(sb[2])
        if not (sb[3] in [None,''] and math.isinf(float(sb[3]))) and (not tb[3] or float(sb[3]) > tb[3]):
            tb[3] = float(sb[3])

'''
if val is str, quote it in expressions
'''
def quoteStr(v):
    if isinstance(v,str): # todo: if '5' is a str, but should be considered int 5
        return f'"{v}"'
    else:
        return v
