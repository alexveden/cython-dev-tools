from string import Template

# title - html page title
# accord_items - text composed with TEMPLATE_PACKAGE
TEMPLATE_ANNOTATE_INDEX = Template("""
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>$title</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.0/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-gH2yIJqKdNHPEq0n4Mqa/HGKIhSkIHeL5AyhkYV8i59U5AR6csBvApHHNl/vI1Bx" crossorigin="anonymous">
</head>
<body>
<div class="container">
    <div class="row">
        <div class="col-3">
            <div class="accordion" id="accordion_packages">
                $accord_items
            </div>
        </div>
        <div class="col">
            <iframe src="" name="iframe_annotation" title="description" style="height: 100vh;" width="100%"></iframe>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.0/dist/js/bootstrap.bundle.min.js" integrity="sha384-A3rJD856KowSb7dwlZdYEkO39Gagi7vIsF0jrRAoQmDKKtQBHUuLZ9AsSv4jD4Xa" crossorigin="anonymous"></script>
</body>
</html>
""")

# package_name - main packagename (used in HTML id)
# package_title - accordion title
# package_contents - package structure/links (another HTML template)
TEMPLATE_PACKAGE = Template("""
<div class="accordion-item">
    <h2 class="accordion-header" id="${package_name}_headingOne">
      <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#${package_name}_collapseOne" aria-expanded="true" aria-controls="${package_name}_collapseOne">
        $package_title
      </button>
    </h2>
    <div id="${package_name}_collapseOne" class="accordion-collapse collapse show" aria-labelledby="${package_name}_headingOne" data-bs-parent="#accordion_packages">
      <div class="accordion-body">
          $package_contents
      </div>
    </div>
  </div>
""")

# url
# label
TEMPLATE_URL = Template("""<a href="${url}" target="iframe_annotation">${label}</a>""")