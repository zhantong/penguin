def custom(app):
    @app.template_test('list')
    def test_list(l):
        return isinstance(l, list)

    @app.template_filter('type')
    def filter_type(t):
        return type(t)
