Internal Server Error: /admin/bookkeepers/
Traceback (most recent call last):
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\base.py", line 577, in parse
    compile_func = self.tags[command]
                   ~~~~~~~~~^^^^^^^^^
KeyError: 'static'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\core\handlers\exception.py", line 55, in inner
    response = get_response(request)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\core\handlers\base.py", line 198, in _get_response
    response = wrapped_callback(request, *callback_args, **callback_kwargs)
  File "C:\Users\Romul\FOR_UI\safebooks\views.py", line 259, in _wrapped_view
    return view_func(request, *args, **kwargs)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\utils\decorators.py", line 192, in _view_wrapper
    result = _process_exception(request, e)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\utils\decorators.py", line 190, in _view_wrapper
    response = view_func(request, *args, **kwargs)
  File "C:\Users\Romul\FOR_UI\safebooks\views.py", line 423, in admin_bookkeepers_page_view
    return render(request, "admin_panel/bookkeepers.html", context)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\shortcuts.py", line 25, in render
    content = loader.render_to_string(template_name, context, request, using=using)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\loader.py", line 61, in render_to_string
    template = get_template(template_name, using=using)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\loader.py", line 15, in get_template
    return engine.get_template(template_name)
           ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\backends\django.py", line 79, in get_template
    return Template(self.engine.get_template(template_name), self)
                    ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\engine.py", line 186, in get_template
    template, origin = self.find_template(template_name)
                       ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\engine.py", line 159, in find_template
    template = loader.get_template(name, skip=skip)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\loaders\cached.py", line 57, in get_template
    template = super().get_template(template_name, skip)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\loaders\base.py", line 28, in get_template
    return Template(
        contents,
    ...<2 lines>...
        self.engine,
    )
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\base.py", line 157, in __init__
    self.nodelist = self.compile_nodelist()
                    ~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\base.py", line 199, in compile_nodelist
    nodelist = parser.parse()
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\base.py", line 585, in parse
    raise self.error(token, e)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\base.py", line 583, in parse
    compiled_result = compile_func(self, token)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\loader_tags.py", line 307, in do_extends
    nodelist = parser.parse()
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\base.py", line 585, in parse
    raise self.error(token, e)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\base.py", line 583, in parse
    compiled_result = compile_func(self, token)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\loader_tags.py", line 235, in do_block
    nodelist = parser.parse(("endblock",))
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\base.py", line 579, in parse
    self.invalid_block_tag(token, command, parse_until)
    ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\template\base.py", line 634, in invalid_block_tag
    raise self.error(
    ...<8 lines>...
    )
django.template.exceptions.TemplateSyntaxError: Template: C:\Users\Romul\FOR_UI\templates\admin_panel\bookkeepers.html, Invalid block tag on line 167: 'static', expected 'endblock'. Did you forget to register or load this tag?
[13/May/2026 20:29:28] "GET /admin/bookkeepers/ HTTP/1.1" 500 199000
[13/May/2026 20:29:29] "GET /favicon.ico HTTP/1.1" 302 0
[13/May/2026 20:29:29] "GET /static/images/Logo_safebooks.png HTTP/1.1" 200 94383
