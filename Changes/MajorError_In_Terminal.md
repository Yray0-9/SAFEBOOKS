[07/May/2026 09:47:08] "GET /favicon.ico HTTP/1.1" 302 0
[07/May/2026 09:47:08] "GET /static/images/Logo_safebooks.png HTTP/1.1" 200 94383
Internal Server Error: /api/clients/
Traceback (most recent call last):
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\db\backends\utils.py", line 105, in _execute
    return self.cursor.execute(sql, params)
           ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\psycopg\cursor.py", line 117, in execute
    raise ex.with_traceback(None)
psycopg.errors.UndefinedColumn: column clients.custom_fields does not exist
LINE 1: ...number", "clients"."birthday", "clients"."email", "clients"....
                                                             ^

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\core\handlers\exception.py", line 55, in inner
    response = get_response(request)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\core\handlers\base.py", line 198, in _get_response
    response = wrapped_callback(request, *callback_args, **callback_kwargs)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\views\decorators\http.py", line 64, in inner
    return func(request, *args, **kwargs)
  File "C:\Users\Romul\FOR_UI\safebooks\views.py", line 182, in _wrapped_view
    return view_func(request, *args, **kwargs)
  File "C:\Users\Romul\FOR_UI\safebooks\views.py", line 411, in clients_api_view
    result = list_clients_for_bookkeeper(request.bookkeeper_account)
  File "C:\Users\Romul\FOR_UI\safebooks\services\client_service.py", line 132, in list_clients_for_bookkeeper
    "clients": [_serialize_client(client) for client in clients],
                                                        ^^^^^^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\db\models\query.py", line 390, in __iter__
    self._fetch_all()
    ~~~~~~~~~~~~~~~^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\db\models\query.py", line 2000, in _fetch_all
    self._result_cache = list(self._iterable_class(self))
                         ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\db\models\query.py", line 95, in __iter__
    results = compiler.execute_sql(
        chunked_fetch=self.chunked_fetch, chunk_size=self.chunk_size
    )
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\db\models\sql\compiler.py", line 1624, in execute_sql
    cursor.execute(sql, params)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\db\backends\utils.py", line 122, in execute
    return super().execute(sql, params)
           ~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\db\backends\utils.py", line 79, in execute
    return self._execute_with_wrappers(
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        sql, params, many=False, executor=self._execute
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\db\backends\utils.py", line 92, in _execute_with_wrappers
    return executor(sql, params, many, context)
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\db\backends\utils.py", line 100, in _execute
    with self.db.wrap_database_errors:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\db\utils.py", line 94, in __exit__
    raise dj_exc_value.with_traceback(traceback) from exc_value
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\django\db\backends\utils.py", line 105, in _execute
    return self.cursor.execute(sql, params)
           ~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
  File "C:\Users\Romul\FOR_UI\.venv\Lib\site-packages\psycopg\cursor.py", line 117, in execute
    raise ex.with_traceback(None)
django.db.utils.ProgrammingError: column clients.custom_fields does not exist
LINE 1: ...number", "clients"."birthday", "clients"."email", "clients"....
                                                             ^
[07/May/2026 09:47:08] "GET /api/clients/ HTTP/1.1" 500 21597