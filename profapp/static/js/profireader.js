function switch_something(element, url, selector_off, selector_on, replace_key_selector) {
    $ok(url, {'on': $(selector_on, element).is(':visible')?false:true}, function (resp) {
        $(selector_off, element).hide();
        $(selector_on, element).hide();
        (resp && resp['on']) ? $(selector_off, element).show() : $(selector_on, element).show();
        if (replace_key_selector)
            $.each(replace_key_selector, function (key, selector) {
                if (key in resp) {
                    $(selector, element).html(resp[key]);
                }
            })
    })
}

 