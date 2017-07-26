tinymce.PluginManager.add('gallery', function (editor, url) {

    var galleryElm = null;

    var get_value_units = function (val) {
        var ret = val.replace(/^\s*/, '').replace(/\s*$/, '');
        var value = ret.replace(/^([+-]?([0-9]*[.])?[0-9]+).*$/, '$1');
        var units = ret.replace(/^[+-]?([0-9]*[.])?[0-9]+/, '');
        return [value, units];
    };

    var round_value = function (val, units) {
        return (parseFloat(val).toFixed(1).replace(/\.?0*$/, '')) + units;
    };


    var dialog_controller = {
        win: null,

        open_window: function () {
            var data = {};
            dialog_controller.win = editor.windowManager.open({
                onSubmit: function () {
                    return false;
                },
                title: 'Article image gallery',
                data: data,
                buttons: [
                    {
                        'text': "Ok",
                        'classes': 'primary image-gallery-save',
                        'onclick': function () {
                            if (!dialog_controller.can_be_saved()) {
                                return false;
                            }
                            dialog_controller.enable_dialog(false, 'Saving...');
                            var data = dialog_controller.win.toJSON();
                            editor_controller.insertGallery(dialog_controller.get_data(),
                                data['gallery_width'], data['gallery_height'], data['constrain_proportions']);
                            dialog_controller.enable_dialog(true);
                            dialog_controller.win.close();
                        }
                    }, {
                        'classes': 'image-gallery-upload',
                        'text': "Upload", onclick: function () {
                            $('.mce-pr-sortable-images div input[type=file]').trigger('click');
                        }
                    }, {
                        'text': "Cancel",
                        'onclick': function () {
                            dialog_controller.win.close();
                        }
                    }
                ],

                bodyType: 'form',
                classes: 'pr-image-gallery-dialog',
                body: [
                    {
                        type: 'container',
                        // label: 'Dimensions',
                        layout: 'flex',
                        direction: 'row',
                        align: 'center',
                        spacing: 5,
                        items: [
                            {
                                text: 'Dimensions', type: 'label', size: 4,
                            },
                            {
                                name: 'gallery_width', type: 'textbox', size: 4, ariaLabel: 'Width',
                                id: 'pr_image_gallery_width',
                                tooltip: 'set width as `X` (pixels) or `X%` (percents of article width)',
                                classes: 'pr-image-gallery-width'
                            },
                            {type: 'label', text: 'x'},
                            {
                                name: 'gallery_height', type: 'textbox', size: 4, ariaLabel: 'Height',
                                id: 'pr_image_gallery_height',
                                tooltip: 'set width as `X` (pixels) or `X%` (percents of gallery width)',
                                classes: 'pr-image-gallery-height'
                            },
                            {
                                name: 'constrain_proportions', type: 'checkbox',
                                classes: 'pr-image-gallery-constrain-proportions',
                                tooltip: 'Keep aspect ratio on resize',
                                id: 'pr-image-gallery-keep-constrain-proportions',
                                onchange: dialog_controller.constrain_proportions,
                                text: 'Constrain proportions'
                            },
                            {
                                name: 'calculate_size', type: 'button', size: 5,
                                classes: 'pr-image-gallery-calculate-size',
                                tooltip: 'Recalculate size to best fit all images',
                                text: 'Fit size',
                            },
                        ]
                    }, {
                        type: 'container',
                        minHeight: 350,
                        minWidth: 500,
                        classes: 'pr-sortable-images'
                    },
                ],
            });
        },


        constrain_proportions: function () {

            dialog_controller.disable_enable_save_gallery();

            var items = dialog_controller.get_data()['items'];
            if (items.length !== 1) {
                return;
            }
            var $height_control = $('#pr_image_gallery_height', $('#' + dialog_controller.win._id));
            if (dialog_controller.win.toJSON()['constrain_proportions']) {
                $height_control.prop('disabled', true).addClass('disabled');
                dialog_controller.get_image_size(items[0], function (w, h) {
                    $height_control.val(round_value(h / w * 100, '%'));
                });
            }
            else {
                $height_control.prop('disabled', false).removeClass('disabled');
            }
        },


        add_custom_html_elements: function () {
            var $container = $('#' + dialog_controller.win._id);
            $container.append('<div class="pr-image-gallery-dialog-dimmed" style="display: none;"></div><div class="pr-image-gallery-dialog-dimmed-text" style="display: none;"><span></span></div>');
            $('.mce-pr-sortable-images div', $container).append('<ul></ul>');
            $('.mce-pr-sortable-images div', $container).append('<input type="file" multiple />');
            $('.mce-pr-sortable-images div input[type=file]', $container).bind('change', dialog_controller.upload_images);
            $('.mce-pr-sortable-images', $container).on('click', '.pr-gallery-item-remove-undo', dialog_controller.remove_undo);
            $('.mce-pr-image-gallery-calculate-size button', $container).prop('disabled', true);
            $('.mce-pr-image-gallery-calculate-size', $container).on('click', 'button', dialog_controller.recalculate_size);
        },

        depict_gallery_and_items_controls: function () {

            $('#' + dialog_controller.win._id + ' .mce-pr-image-gallery-width').val(editor_controller.default_width);
            $('#' + dialog_controller.win._id + ' .mce-pr-image-gallery-height').val(editor_controller.default_height);
            if (galleryElm) {
                dialog_controller.enable_dialog(false);

                $('#' + dialog_controller.win._id + ' .mce-pr-image-gallery-width').val(editor_controller.normalizeWidthHeight($(galleryElm), 'width'));
                $('#' + dialog_controller.win._id + ' .mce-pr-image-gallery-height').val(editor_controller.normalizeWidthHeight($(galleryElm), 'height'));
                dialog_controller.win.find('#constrain_proportions')[0].checked(galleryElm.getAttribute('data-mce-image-gallery-constrain-proportions') === 'true');
                var gallery_id = editor_controller.get_id_from_element(galleryElm);
                var gallery_data = editor.getParam('gallery_get_data')(gallery_id);
                if (!gallery_data) {
                    dialog_controller.enable_dialog(true);
                    add_message('error loading gallery gallery_id=' + gallery_id);
                    dialog_controller.win.close();
                    return;
                }

                var images_container = dialog_controller.get_image_container();
                images_container.html('');
                $.each(gallery_data['items'], function (index, item) {
                    dialog_controller.append_image(item['id'], item['title'], item['copyright'], item['background_image']);
                });
                dialog_controller.disable_enable_save_gallery();
                dialog_controller.enable_dialog(true);
            }
        },

        get_image_container: function () {
            return $('#' + dialog_controller.win._id + ' ul');
        },

        upload_images: function (event) {
            var the_files = (event.target.files && event.target.files.length) ? event.target.files : [];
            var uploaders = [];
            var filesreaded = 0;
            var old_image_count = dialog_controller.get_data()['items'].length;


            var read_file_progress = function () {
                filesreaded++;
                if (filesreaded == uploaders.length) {
                    if (!old_image_count) {
                        dialog_controller.recalculate_size();
                    }
                    dialog_controller.enable_dialog(true);
                }
                else {
                    dialog_controller.enable_dialog(false, 'Reading file ' + filesreaded + ' of ' + uploaders.length + '...');
                }
                dialog_controller.disable_enable_save_gallery();
            };

            for (var i = 0; i < the_files.length; i++) {
                uploaders.push(new FileReader());
                uploaders[i].onload = (function (the_file, uploader) {
                    return function (e) {
                        var beginstr = uploader.result.substr(0, 50);
                        if (beginstr.match(/^data:image\/(png|gif|jpeg);base64/g)) {
                            dialog_controller.append_image('', the_file.name, the_file.copyright, 'url(' + uploader.result + ')', the_files.type);
                            read_file_progress();
                        }
                        else {
                            uploader.onerror(e);
                        }
                    }
                })(the_files[i], uploaders[i]);

                uploaders[i].onerror = (function (the_file, uploader) {
                    return function (e) {
                        add_message('File loading error: `' + the_file.name + '`', 'warning');
                        read_file_progress();
                    }
                })(the_files[i], uploaders[i]);

                uploaders[i].readAsDataURL(the_files[i]);
            }
            $(this).val('');
        },

        remove_undo: function (event) {
            var $li = $(event.currentTarget).closest('li');
            var is_disabled = $('input.pr-gallery-item-title', $li).is(':disabled');
            $('input', $li).prop('disabled', is_disabled ? false : true);
            is_disabled ? $('input,img', $li).removeClass('disabled') : $('input,img', $li).addClass('disabled');
            $('.pr-gallery-item-remove-undo', $li).html(is_disabled ? 'Remove' : 'Undo');
            dialog_controller.disable_enable_save_gallery();
            event.preventDefault();
        },

        disable_enable_save_gallery: function () {
            console.log('disable_enable_save_gallery');
            var $context = $('#' + dialog_controller.win._id);
            var images_container = this.get_image_container();
            var image_numbers = 0;
            $('li', images_container).each(function (ind, $li) {
                if (!$('input.pr-gallery-item-title', $li).is(':disabled')) {
                    image_numbers++;
                }
            });
            $('.mce-image-gallery-save button', $context).prop('disabled', image_numbers ? false : true);
            $('.mce-pr-image-gallery-calculate-size button', $context).prop('disabled', image_numbers ? false : true);

            var chkbox = dialog_controller.win.find('#constrain_proportions')[0];

            if (image_numbers === 1) {
                $('.mce-pr-image-gallery-constrain-proportions', $context).removeClass('disabled');
                chkbox.disabled(false);
            }
            else {
                $('.mce-pr-image-gallery-constrain-proportions', $context).addClass('disabled');
                chkbox.disabled(true);
                chkbox.checked(false);
                $('#pr_image_gallery_height', $context).prop('disabled', false).removeClass('disabled');
            }
            return (image_numbers ? false : true);
        },

        can_be_saved: function () {
            return !$('.mce-image-gallery-save button', $('#' + dialog_controller.win._id)).is(':disabled') && !$('.pr-image-gallery-dialog-dimmed', $('#' + dialog_controller.win._id)).is(":visible");
        },

        enable_dialog: function (enable, text) {
            if (enable) {
                $('#' + dialog_controller.win._id + ' .pr-image-gallery-dialog-dimmed').hide();
                $('#' + dialog_controller.win._id + ' .pr-image-gallery-dialog-dimmed-text').hide();
                $('span', '#' + dialog_controller.win._id + ' .pr-image-gallery-dialog-dimmed-text').text('');

            }
            else {
                $('span', '#' + dialog_controller.win._id + ' .pr-image-gallery-dialog-dimmed-text').text(text ? text : 'Loading...');
                $('#' + dialog_controller.win._id + ' .pr-image-gallery-dialog-dimmed-text').show();
                $('#' + dialog_controller.win._id + ' .pr-image-gallery-dialog-dimmed').show();
            }
        },

        add_html: function () {
            var images_container = this.get_image_container();
            var ret = $('<li>' +
                '<img class="pr-gallery-item-preview" src="' + static_address('images/0.gif') + '" />' +
                '<input class="pr-gallery-item-id" hidefocus="1" type="hidden"/>' +
                '<input class="mce-textbox mce-first pr-gallery-item-title" hidefocus="1" placeholder="title"/>' +
                '<input class="mce-textbox pr-gallery-item-copyright" hidefocus="1" placeholder="copyright"/>' +
                '<div class="mce-btn"><button role="presentation" type="button" tabindex="-1" class="pr-gallery-item-remove-undo">Remove</button></div>' +
                '</li>');
            images_container.append(ret);
            images_container.sortable({
                axis: "y",
                containment: $('.mce-pr-sortable-images div'),
                handle: "img"
            });
            images_container.disableSelection();
            return ret;

        },

        append_image: function (item_id, file_title, file_copyright, file_background, file_mime) {
            var container_row = this.add_html();
            $('img', container_row).css({backgroundImage: file_background});
            $('.pr-gallery-item-id', container_row).val(item_id);
            $('.pr-gallery-item-title', container_row).val(file_title);
            $('.pr-gallery-item-copyright', container_row).val(file_copyright);
        },

        get_data: function () {
            var items = [];
            $('li', '#' + dialog_controller.win._id + ' ul').each(function (index, $li) {
                if (!$('input.pr-gallery-item-title', $li).is(':disabled')) {
                    items.push({
                        'id': $('.pr-gallery-item-id', $li).val(),
                        'position': items.length + 1,
                        'title': $('.pr-gallery-item-title', $li).val(),
                        'copyright': $('.pr-gallery-item-copyright', $li).val(),
                        'background_image': $('img', $li).css('backgroundImage'),
                    });
                }
            });
            return {
                'id': editor_controller.get_id_from_element(galleryElm),
                'items': items
            };
        },

        get_image_size: function (item, callback) {
            var src = item['background_image'].replace(/^url\(['"]?/g, '').replace(/['"]?\)$/g, '');
            // Create dummy image to get real width and height
            $("<img>").attr("src", src).load(function () {
                callback(this.width, this.height);
            });
        },

        recalculate_size: function () {
            if (dialog_controller.can_be_saved()) {
                var scale = 1;
                // var area = 1;
                var items = dialog_controller.get_data()['items'];
                var cnt = items.length;
                var loaded = 0;
                dialog_controller.enable_dialog(false, 'Calculate...');
                $.each(items, function (ind, item) {
                    dialog_controller.get_image_size(item,
                        function (w, h) {
                            // area = area * Math.pow(w * h, 1. / cnt);
                            scale = scale * Math.pow(w / h, 1. / cnt);
                            loaded++;
                            if (loaded == cnt) {
                                $('.mce-pr-image-gallery-width', '#' + dialog_controller.win._id).val('100%');
                                $('.mce-pr-image-gallery-height', '#' + dialog_controller.win._id).val(Math.round(100 / scale) + '%');
                                dialog_controller.enable_dialog(true, '');
                            }
                        })
                });
            }
        },
    };

    var editor_controller = {

        prefix: 'data-mce-pr-image-gallery-',
        default_width: '100%',
        default_height: '50%',

        get_iframe_conent: function () {
            return $(editor.iframeElement).contents()[0];
        },

        getSheet: function () {
            // Create the <style> tag
            var iframe_content = editor_controller.get_iframe_conent();

            var csssheet = $.grep(iframe_content.styleSheets, function (el) {
                return el.title == 'gallery_preview_css_rules'
            });
            if (csssheet.length) {
                return csssheet[0];
            }


            var style = iframe_content.createElement('style');
            style.setAttribute('title', 'gallery_preview_css_rules');

            // WebKit hack :(
            style.appendChild(document.createTextNode(''));

            // Add the <style> element to the page
            iframe_content.head.appendChild(style);

            return style.sheet;
        },

        deleteOldCSSRule: function (gallery_id) {
            var sheet = this.getSheet();
            var todelete = [];
            $.each(sheet.cssRules, function (ind, arule) {
                if (arule.selectorText.match(gallery_id)) {
                    todelete.push(ind);
                }
            });
            todelete.reverse();
            $.each(todelete, function (ind, todelind) {
                sheet.deleteRule(todelind);
            });

        },

        addCSSRule: function (gallery_id, background_image, index) {
            editor_controller.deleteOldCSSRule(gallery_id);
            var sheet = this.getSheet();
            var rule = 'background-image: ' + background_image + ';'
            var className = 'data-mce-image-gallery-placeholder-' + gallery_id;
            sheet.insertRule('.' + className + " {" + rule + "}", index ? index : 0);
            return className;
        },

        normalizeWidthHeight: function ($img, attr_name) {
            var def_value = ((attr_name == 'width') ? editor_controller.default_width : editor_controller.default_height);
            var ret = $img.attr(editor_controller.prefix + attr_name);
            if (ret === undefined) {
                ret = $img.attr(attr_name);
                ret = (ret === undefined) ? def_value : ret;
                $img.attr(editor_controller.prefix + attr_name, ret);
            }

            var val_units = get_value_units(ret);
            return val_units[0] + (val_units[1] == '' ? 'px' : val_units[1]);
        },

        resizeGallery: function ($img) {
            var width = editor_controller.normalizeWidthHeight($img, 'width');
            var height = editor_controller.normalizeWidthHeight($img, 'height');
            $img.css({'width': width});
            if (height.match(/%$/)) {
                height = '' + (parseFloat(height.replace(/%\s*$/, '')) / 100. * $img.width()) + 'px';
            }
            $img.css({'height': height});
        },

        updateGalleryElement: function ($img, gallery_data) {
            editor_controller.resizeGallery($img);
            var title = (gallery_data['items'].length == 1) ? 'only one image' : ((gallery_data['items'].length - 1) + ' more image(s)');
            var background_class = (gallery_data['items'].length ? editor_controller.addCSSRule(gallery_data['id'], gallery_data['items'][0]['background_image']) : '');
            $img.attr('title', title);
            $img.addClass(background_class);
            $img.attr('width', $img.width());
            $img.attr('height', $img.height());
            return $img;
        },


        setSize: function ($img, rel_w, rel_h) {
            $img.attr(editor_controller.prefix + 'width', rel_w);
            $img.attr(editor_controller.prefix + 'height', rel_h);
        },

        insertGallery: function (gallery_data, w, h, constrain_proportions) {
            editor.insertContent(
                '<img class="data-mce-image-gallery-placeholder"' +
                ' src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"' +
                ' data-mce-placeholder ' +
                ' data-mce-image-gallery-placeholder="' + gallery_data['id'] + '"' +
                ' data-mce-image-gallery-constrain-proportions="' + constrain_proportions + '"' +
                ' >');
            gallery_data['items'].sort(function (a, b) {
                return (a['position'] < b['position']) ? -1 : ((a['position'] > b['position']) ? 1 : 0);
            });
            editor.getParam('gallery_set_data')(gallery_data['id'], gallery_data);
            var $img = $('img[data-mce-image-gallery-placeholder=' + gallery_data['id'] + ']', editor_controller.get_iframe_conent());
            editor_controller.setSize($img, w, h);
            editor_controller.updateGalleryElement($img, gallery_data);


        },

        get_id_from_element: function (element) {
            if (!element) {
                return randomHash();
            }
            return $(element).attr('data-mce-image-gallery-placeholder');
        },

    };

    editor.on('ResolveName', function (e) {
        if (e.target.nodeType == 1 && (e.target.getAttribute("data-mce-image-gallery-placeholder"))) {
            e.name = 'image gallery';
        }
    });

    editor.on('init', function (e) {
        editor_controller.getSheet();
        setTimeout(function () {
            $('img[data-mce-image-gallery-placeholder]', $(editor_controller.get_iframe_conent())).each(function (ind, img) {
                var $img = $(img);
                var gallery_id = editor_controller.get_id_from_element($img);
                var gallery_data = editor.getParam('gallery_get_data')(gallery_id);
                if (!gallery_data) {
                    add_message('error loading gallery gallery_id=' + gallery_id)
                }
                else {
                    editor_controller.updateGalleryElement($img, gallery_data);
                }
            });
        }, 100);

    });

    editor.on('ObjectResizeStart', function (e) {
        $(e.target).data(editor_controller.prefix + 'original_size', [$(e.target).width(), $(e.target).height()]);
    });

    editor.on('ObjectResized', function (e) {
        var scale = function (size_name, new_w, new_h, old_w, old_h) {
            var ratio = ((size_name == 'width') ? new_w / old_w : new_h / old_h);
            var val = editor_controller.normalizeWidthHeight($img, size_name);
            var value_units = get_value_units(val);
            if (size_name == 'height' && value_units[1] == '%') {
                ratio /= new_w / old_w;
            }

            return round_value(parseFloat(value_units[0]) * ratio, value_units[1]);
        };

        var $img = $(e.target);
        var old_values = $img.data(editor_controller.prefix + 'original_size');
        var new_values = [$img.width(), $img.height()];

        editor_controller.setSize($img,
            scale('width', new_values[0], new_values[1], old_values[0], old_values[1]),
            scale('height', new_values[0], new_values[1], old_values[0], old_values[1]));

        $img.attr(editor_controller.prefix + 'constrain-proportions', false);
    });


    editor.addButton('gallery', {
        text: 'Gallery',
        icon: 'image',
        stateSelector: 'img[data-mce-image-gallery-placeholder]',
        onclick: function () {
            galleryElm = editor.selection.getNode();
            if (!galleryElm || galleryElm.nodeName != 'IMG' || !galleryElm.getAttribute('data-mce-image-gallery-placeholder')) {
                galleryElm = null;
            }
            dialog_controller.open_window();
            dialog_controller.add_custom_html_elements();
            dialog_controller.depict_gallery_and_items_controls();
        }
    });
});

