tinymce.PluginManager.add('gallery', function (editor, url) {

    var galleryElm = null;

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
                                data['gallery_width'], data['gallery_height']);
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
                        label: 'Dimensions',
                        layout: 'flex',
                        direction: 'row',
                        align: 'center',
                        spacing: 5,
                        items: [
                            {
                                name: 'gallery_width', type: 'textbox', size: 3, ariaLabel: 'Width',
                                'classes': 'pr-image-gallery-width'
                            },
                            {type: 'label', text: 'x'},
                            {
                                name: 'gallery_height', type: 'textbox', size: 3, ariaLabel: 'Height',
                                'classes': 'pr-image-gallery-height'
                            },
                            {
                                name: 'calculate_size', type: 'button', size: 5,
                                'classes': 'pr-image-gallery-calculate-size',
                                text: 'Recalculate'
                            }
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

        add_custom_html_elements: function () {
            $('#' + dialog_controller.win._id).append('<div class="pr-image-gallery-dialog-dimmed" style="display: none;"></div><div class="pr-image-gallery-dialog-dimmed-text" style="display: none;"><span></span></div>');
            $('#' + dialog_controller.win._id + ' .mce-pr-sortable-images div').append('<ul></ul>');
            $('#' + dialog_controller.win._id + ' .mce-pr-sortable-images div').append('<input type="file" multiple />');
            $('#' + dialog_controller.win._id + ' .mce-pr-sortable-images div input[type=file]').bind('change', dialog_controller.upload_images);
            $('#' + dialog_controller.win._id + ' .mce-pr-sortable-images').on('click', '.pr-gallery-item-remove-undo', dialog_controller.remove_undo);
            $('#' + dialog_controller.win._id + ' .mce-pr-image-gallery-calculate-size button').prop('disabled', true);
            $('#' + dialog_controller.win._id + ' .mce-pr-image-gallery-calculate-size').on('click', 'button', dialog_controller.recalculate_size);
        },

        depict_gallery_and_items_controls: function () {

            $('#' + dialog_controller.win._id + ' .mce-pr-image-gallery-width').val('100%');
            $('#' + dialog_controller.win._id + ' .mce-pr-image-gallery-height').val('200');
            if (galleryElm) {
                dialog_controller.enable_dialog(false);

                $('#' + dialog_controller.win._id + ' .mce-pr-image-gallery-width').val($(galleryElm).attr('width'));
                $('#' + dialog_controller.win._id + ' .mce-pr-image-gallery-height').val($(galleryElm).attr('height'));
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
                    dialog_controller.enable_dialog(true);
                    if (!old_image_count) {
                        dialog_controller.recalculate_size();
                    }
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
            var images_container = this.get_image_container();
            var is_disabled = true;
            $('li', images_container).each(function (ind, $li) {
                is_disabled = is_disabled && $('input.pr-gallery-item-title', $li).is(':disabled');
            });
            $('.mce-image-gallery-save button', $('#' + dialog_controller.win._id)).prop('disabled', is_disabled);
            $('.mce-pr-image-gallery-calculate-size button', $('#' + dialog_controller.win._id)).prop('disabled', is_disabled);
            return is_disabled;
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

        recalculate_size: function () {
            if (dialog_controller.can_be_saved()) {
                var scale = 1;
                var area = 1;
                var items = dialog_controller.get_data()['items'];
                var cnt = items.length;
                var loaded = 0;
                dialog_controller.enable_dialog(false, 'Calculate...');
                $.each(items, function (ind, item) {
                    // Create dummy image to get real width and height
                    $("<img>").attr("src",
                        item['background_image'].replace(/^url\(['"]?/g, '').replace(/['"]?\)$/g, '')
                    ).load(function () {
                        area = area * Math.pow(this.width * this.height, 1./cnt);
                        scale = scale * Math.pow(this.width/this.height, 1./cnt);
                        loaded++;
                        if (loaded == cnt) {
                            $('.mce-pr-image-gallery-width', '#' + dialog_controller.win._id).val(
                                Math.round(Math.pow(area*scale, 0.5)));
                            $('.mce-pr-image-gallery-height', '#' + dialog_controller.win._id).val(
                                Math.round(Math.pow(area/scale, 0.5)));
                            dialog_controller.enable_dialog(true, '');
                        }
                    });
                });
            }
        },
    };

    var editor_controller = {

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

        updateGalleryElement: function (gallery_data) {
            var $img = $('img[data-mce-image-gallery-placeholder=' + gallery_data['id'] + ']', editor_controller.get_iframe_conent());
            var title = (gallery_data['items'].length == 1) ? 'only one image' : ((gallery_data['items'].length - 1) + ' more image(s)');
            var background_class = (gallery_data['items'].length ? editor_controller.addCSSRule(gallery_data['id'], gallery_data['items'][0]['background_image']) : '');
            $img.attr('title', title);
            $img.addClass(background_class);
        },

        insertGallery: function (gallery_data, w, h) {

            editor.insertContent(
                '<img width="' + w + '" height="' + h + '" class="data-mce-image-gallery-placeholder"' +
                ' src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"' +
                ' data-mce-placeholder ' +
                ' data-mce-image-gallery-placeholder="' + gallery_data['id'] + '">');
            console.log(gallery_data['items']);
            gallery_data['items'].sort(function (a, b) {
                return (a['position'] < b['position']) ? -1 : ((a['position'] > b['position']) ? 1 : 0);
            });
            editor.getParam('gallery_set_data')(gallery_data['id'], gallery_data);
            editor_controller.updateGalleryElement(gallery_data);
        },

        get_id_from_element: function (element) {
            if (!element) {
                return randomHash();
            }
            return $(element).attr('data-mce-image-gallery-placeholder');
        },

        // get_first_image_id_from_element: function (element) {
        //     if (!element) {
        //         return null;
        //     }
        //     var ret = $(element).attr('data-mce-image-gallery-placeholder').replace(/^.*:/, '');
        //     return ret ? ret : null;
        // },

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
                    editor_controller.updateGalleryElement(gallery_data);
                }
            });
        }, 100);
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

