#coding=utf8
from uliweb import functions, url_for
import logging
from forms import QueryForm

log = logging.getLogger(__name__)
class Default(object):pass

class MultiView(object):
    """
    Multi View Class

    Support: list, add, delete, edit, detail, etc
    """

    def _process_fields_convert_map(self, parameters, download=False):
        """
        process fields_convert_map, ListView doesn't support list type but dict

        fields_convert_map should be define as list or dict
        for list, it can be:
            [name, name, ...]
            [(name, func), (name, func), ...] if func is str, it'll be the property name of class
        for dict, it can be:
            {'name':func, ...}
        :param model: model object
        :param parameters:
        :param prefix: it'll used to combine prefix+_convert_xxx to get convert function
            from class
        :return:
        """
        if 'fields_convert_map' in parameters:
            _f = parameters.get('fields_convert_map') or []
            parameters['fields_convert_map'] = self._get_fields_convert_map(_f, download)


    def _get_fields_convert_map(self, fields, download=False):
        """
        process fields_convert_map, ListView doesn't support list type but dict

        fields_convert_map should be define as list or dict
        for list, it can be:
            [name, name, ...]
            [(name, func), (name, func), ...] if func is str, it'll be the property name of class
        for dict, it can be:
            {'name':func, ...}
        :param model: model object
        :param parameters:
        :param prefix: it'll used to combine prefix+_convert_xxx to get convert function
            from class
        :return:
        """
        _f = fields
        t = {}

        # add support for download field
        def _get(name):
            _name = '_convert_download_{}'.format(name)
            if download and hasattr(self, _name):
                return getattr(self, _name)
            return getattr(self, '_convert_{}'.format(name))

        if isinstance(_f, list):
            for k in _f:
                if isinstance(k, str):
                    t[k] = _get(k)
                elif isinstance(k, (tuple, list)):
                    name = k[0]
                    func = k[1]
                    if isinstance(func, str):
                        t[name] = _get(func)
                    elif callable(func):
                        t[name] = func
                    else:
                        raise ValueError("Fields convert function should be str or callable, but %r found" % type(func))
                else:
                    raise ValueError("Fields convert element should be str or tuple or list, but %r found" % type(k))
        elif isinstance(_f, dict):
            for k, v in _f.items():
                if isinstance(v, str):
                    t[k] = _get(v)
                elif callable(v):
                    t[k] = v
                else:
                    raise ValueError("Fields convert function should be str or callable, but %r found" % type(func))
        return t

    def _list_view(self, model, **kwargs):
        """
        :param model:
        :param fields_convert_map: it's different from ListView
        :param kwargs:
        :return:
        """
        view =  functions.ListView(model, **kwargs)
        return view


    def _query_view(self, model, **kwargs):
        """
        :param model:
        :return: (query, condition)

        Default use QueryForm
        """
        QueryForm = functions.get_form('QueryForm')

        if 'form_cls' not in kwargs:
            kwargs['form_cls'] = QueryForm
        query = functions.QueryView(model, **kwargs)
        return query


    def _list(self, model, queryview=None, queryform=None, **kwargs):
        from uliweb import request, json, CONTENT_TYPE_JSON
        from sqlalchemy import and_
        from uliweb.utils.generic import get_sort_field
        import copy

        if queryview:
            queryview.run()
            condition = queryview.get_condition()
            post_query_condition = kwargs.get('post_query_condition')
            if post_query_condition:
                condition = post_query_condition(condition)
        else:
            condition = None

        if 'condition' in kwargs:
            condition = and_(condition, kwargs['condition'])

        post_condition = kwargs.get('post_condition')
        if post_condition:
            condition = post_condition(condition)
        kwargs['condition'] = condition


        #process order
        order_by = get_sort_field(model)
        if order_by is not None:
            kwargs['order_by'] = order_by

        _fields = copy.copy(kwargs.get('fields_convert_map', []))

        self._process_fields_convert_map(kwargs)
        downloads = {}
        downloads['filename'] = kwargs.pop('download_filename', 'download.xlsx')
        downloads['action'] = kwargs.pop('download_action', 'download')
        downloads['fields_convert_map'] = kwargs.pop('download_fields_convert_map',
                                                  _fields)
        downloads['domain'] = kwargs.pop('download_domain', '')
        downloads['timeout'] = 0
        downloads.update(kwargs.pop('download_kwargs', {}))
        self._process_fields_convert_map(downloads, download=True)

        #get list view
        view = self._list_view(model=model, **kwargs)

        if 'data' in request.values and request.is_xhr:
            return json(view.json(), content_type=CONTENT_TYPE_JSON)
        elif 'download' in request.GET:
            return view.download(**downloads)
        else:
            result = view.run()
            if queryview:
                result.update({'query_form':queryform or queryview.form})
            else:
                result.update({'query_form':''})
            result.update({'table':view})
            return result

    def _view(self, model, obj, **kwargs):
        self._process_fields_convert_map(kwargs)

        view = functions.DetailView(model, obj=obj, **kwargs)
        return view.run()

    def _add(self, model, json_result=False, **kwargs):
        self._process_fields_convert_map(kwargs)

        view = functions.AddView(model, **kwargs)
        return view.run(json_result=json_result)

    def _edit(self, model, obj, json_result=False, **kwargs):
        self._process_fields_convert_map(kwargs)

        view = functions.EditView(model, obj=obj, **kwargs)
        return view.run(json_result=json_result)

    def _delete(self, model, obj, json_result=False, **kwargs):
        view = functions.DeleteView(model, obj=obj, **kwargs)
        return view.run(json_result=json_result)

    def _select_list(self, queryview=None, queryform=None,
                     download_filename=None, **kwargs):
        from uliweb import request, json

        if queryview:
            queryview.run()
            condition = queryview.get_condition()
        else:
            condition = None

        if 'condition' in kwargs:
            condition = and_(condition, kwargs['condition'])
            kwargs['condition'] = condition
        else:
            kwargs['condition'] = condition

        view = functions.SelectListView(**kwargs)
        if 'data' in request.values:
            return json(view.json())
        elif 'download' in request.GET:
            filename = download_filename or 'download.xls'
            kwargs.setdefault('action', 'download')
            kwargs.setdefault('timeout', 0)
            return view.download(filename, **kwargs)
        else:
            result = view.run()
            if queryview:
                result.update({'query_form':queryform or queryview.form})
            else:
                result.update({'query_form':''})
            result.update({'table':view})
            return result

    def _search(self, model, condition=None, search_field='name',
                value_field='id', label_field=None, pagination=True):
        """
        Default search function
        :param search_field: Used for search field, default is 'name'
        :param value_field: Used for id field, default is id
        :param label_field: Used for label field, default is None, then it'll use unicode() function
        """
        from uliweb import json, request

        name = request.GET.get('term', '')
        M = functions.get_model(model)

        def _v(label_field):
            if label_field:
                return lambda x: getattr(x, label_field)
            else:
                return lambda x: unicode(x)

        v_field = request.values.get('label', 'title')
        page = int(request.values.get('page') or 1)
        limit = int(request.values.get('limit') or 10)
        v_func = _v(label_field)
        if name:
            if condition is None:
                condition = M.c[search_field].like('%' + name + '%')
            if pagination:
                query = M.filter(condition)
                total = query.count()
                rows = [{'id': getattr(obj, value_field), v_field: v_func(obj)}
                            for obj in query.limit(limit).offset((page-1)*limit)]
                result = {'total':total, 'rows':rows}
            else:
                result = [{'id': getattr(obj, value_field), v_field: v_func(obj)}
                      for obj in M.filter(condition)]
        else:
            result = []
        return json(result)
