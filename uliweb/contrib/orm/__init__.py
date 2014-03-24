from uliweb import settings

def after_init_apps(sender):
    from uliweb import orm
    from uliweb.utils.common import import_attr
    from uliweb.core.SimpleFrame import __app_alias__
    
    orm.set_debug_query(settings.get_var('ORM/DEBUG_LOG'))
    orm.set_auto_create(settings.get_var('ORM/AUTO_CREATE'))
    orm.set_pk_type(settings.get_var('ORM/PK_TYPE'))
    orm.set_auto_set_model(False)
    orm.set_lazy_model_init(True)
    orm.set_check_max_length(settings.get_var('ORM/CHECK_MAX_LENGTH'))
    orm.set_nullable(settings.get_var('ORM/NULLABLE'))
    orm.set_server_default(settings.get_var('ORM/SERVER_DEFAULT'))
    orm.set_manytomany_index_reverse(settings.get_var('ORM/MANYTOMANY_INDEX_REVERSE'))
    convert_path = settings.get_var('ORM/TABLENAME_CONVERTER')
    convert = import_attr(convert_path) if convert_path else None
    orm.set_tablename_converter(convert)
    
    patch_none = settings.get_var('ORM/PATCH_NONE')
    if patch_none:
        from sqlalchemy.sql.compiler import SQLCompiler
        if patch_none == 'empty':
            setattr(SQLCompiler, 'visit_null', visit_null_empty)
        elif patch_none == 'exception':
            setattr(SQLCompiler, 'visit_null', visit_null_exception)
    
    #judge if transaction middle has not install then set
    #AUTO_DOTRANSACTION is False
    if 'transaction' in settings.MIDDLEWARES:
        orm.set_auto_transaction(True)
    else:
        orm.set_auto_transaction(settings.get_var('ORM/AUTO_TRANSACTION'))
    
    d = {'connection_string':settings.get_var('ORM/CONNECTION'),
        'connection_type':settings.get_var('ORM/CONNECTION_TYPE'),
        'debug_log':settings.get_var('ORM/DEBUG_LOG'),
        'connection_args':settings.get_var('ORM/CONNECTION_ARGS'),
        'strategy':settings.get_var('ORM/STRATEGY'),
        }
    orm.engine_manager.add('default', d)
    
    for name, d in settings.get_var('ORM/CONNECTIONS').items():
        x = {'connection_string':d.get('CONNECTION', ''),
            'debug_log':d.get('DEBUG_LOG', None),
            'connection_args':d.get('CONNECTION_ARGS', {}),
            'strategy':d.get('STRATEGY', 'threadlocal'),
            'connection_type':d.get('CONNECTION_TYPE', 'long')
        }
        orm.engine_manager.add(name, x)

    if 'MODELS_CONFIG' in settings:
        for name, v in settings.MODELS_CONFIG.items():
            orm.set_model_config(name, v)
    
    if 'MODELS' in settings:
        for name, model_path in settings.MODELS.items():
            if not model_path: continue
            if isinstance(model_path, (str, unicode)):
                path = model_path
            else:
                raise Exception("Model path should be a string but %r found" % model_path)
            
            for k, v in __app_alias__.iteritems():
                if path.startswith(k):
                    path = v + path[len(k):]
                    break
            orm.set_model(path, name)

def visit_null_empty(self, expr, **kw):
    return ''

def visit_null_exception(self, expr, **kw):
    raise Exception("You chould not use None in sql condition")
