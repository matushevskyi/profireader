/**
 * Created by oles on 12/19/16.
 */

module.directive('prFileChange', function () {
    return {
        restrict: 'A',
        link: function (scope, element, attrs) {
            var onChangeHandler = scope.$eval(attrs.prFileChange);
            element.bind('change', onChangeHandler);
        }
    };
}).directive('prCrop', function ($compile, $templateCache, $timeout) {
    return {
        restrict: 'A',
        replace: false,
        terminal: true,
        priority: 1000,
        scope: {
            prCrop: '='
        },
        link: function link(scope, element, attrs) {
            element.attr('ng-crop', 'selectedurl');
            element.attr('ng-crop-coordinates', 'coordinates');
            element.attr('ng-crop-options', 'options');
            element.attr('ng-crop-zoom', 'zoom');
            element.attr('ng-crop-origin', 'origin');
            element.attr('logic', 'logic');
            element.attr('ng-crop-disabled', 'disabled');
            element.attr('ng-crop-loading', 'loading');

            element.attr('ng-crop-on-error', 'onerror');
            element.attr('ng-crop-on-load', 'onload');


            element.removeAttr("pr-crop");

            scope.logic = null;
            scope.zoomable = true;
            scope.disabled = false;
            scope.original_model = null;
            scope.preset_button_classes = {'gravatar': 'fa-gravatar'};


            scope.onerror = function (m) {
                add_message(m, 'warning')
            };


            scope.$watch('zoom', function (newv, oldv) {
                    if (newv) {
                        if (!scope.prCrop['selected_by_user']['crop'])
                            scope.prCrop['selected_by_user']['crop'] = {};
                        scope.prCrop['selected_by_user']['crop']['origin_zoom'] = newv;
                    }
                }
            );

            scope.$watch('origin', function (newv, oldv) {
                    if (newv) {
                        if (!scope.prCrop['selected_by_user']['crop'])
                            scope.prCrop['selected_by_user']['crop'] = {};
                        if (newv) {
                            scope.prCrop['selected_by_user']['crop']['origin_left'] = newv[0];
                            scope.prCrop['selected_by_user']['crop']['origin_top'] = newv[1];
                        }
                        else {
                            scope.prCrop['selected_by_user']['crop']['origin_left'] = 0;
                            scope.prCrop['selected_by_user']['crop']['origin_top'] = 0;
                        }

                    }
                }
            );

            scope.$watchCollection('coordinates', function (newv, oldv) {
                if (newv) {
                    if (!scope.prCrop['selected_by_user']['crop'])
                        scope.prCrop['selected_by_user']['crop'] = {};
                    scope.prCrop['selected_by_user']['crop']['crop_left'] = newv[0];
                    scope.prCrop['selected_by_user']['crop']['crop_top'] = newv[1];
                    scope.prCrop['selected_by_user']['crop']['crop_width'] = newv[2] - newv[0];
                    scope.prCrop['selected_by_user']['crop']['crop_height'] = newv[3] - newv[1];
                }
            });

            scope.$watch('prCrop', function (newv, oldv) {
                // console.log('prCrop prCrop', newv, oldv);
                // scope.preset_urls = scope.prCrop ? scope.prCrop['preset_urls'] : {};
                if (!newv) return;
                // console.log(newv);

                // scope.model_name = attrs['prCrop'].split('.').pop();

                var selected_by_user = newv['selected_by_user'];
                var cropper_options = newv['cropper'];
                // console.log(cropper_options);
                // if (!scope.original_model) {

                scope.preset_urls = cropper_options['preset_urls'] ? cropper_options['preset_urls'] : {};
                scope.original_model = $.extend(true, {}, selected_by_user);
                // }
                scope.coordinates = [];
                scope.state = {};
                scope.browsable = cropper_options['browse'] ? true : false;
                scope.uploadable = cropper_options['upload'] ? true : false;
                scope.resetable = true;
                scope.noneurl = cropper_options['no_selection_url'];
                scope.options = {};
                if (cropper_options.min_size) {
                    scope.options['min_width'] = cropper_options.min_size[0];
                    scope.options['min_height'] = cropper_options.min_size[1];
                }

                if (cropper_options.aspect_ratio) {
                    scope.options['min_aspect'] = cropper_options.aspect_ratio[0];
                    scope.options['max_aspect'] = cropper_options.aspect_ratio[1];
                }
                scope.setModel(selected_by_user, false);
            });

            scope.selectPresetUrl = function (preset_id) {
                if (scope.preset_urls && scope.preset_urls[preset_id]) {
                    scope.setModel({'type': 'preset', 'preset_id': preset_id});
                }
            };

            var callback_name = 'pr_cropper_image_selected_in_filemanager_callback_' + scope.controllerName + '_' + randomHash();


            window[callback_name] = function (item) {
                scope.setModel({'type': 'browse', 'image_file_id': item.id, crop_coordinates: null});
                closeFileManager();
            };

            scope.selectNone = function () {
                scope.setModel({'type': 'none'});
            };

            scope.resetModel = function () {
                scope.setModel($.extend(true, {}, scope.original_model));
            };


            scope.setModel = function (model, do_not_set_ng_crop) {

                // console.log('set_model', model);

                switch (model['type']) {
                    case 'browse':
                        // console.log(model);
                        scope.selectedurl = fileUrl(model['image_file_id']);
                        scope.disabled = false;
                        scope.coordinates = null;
                        scope.zoom = null;
                        scope.origin = null;
                        break;
                    case 'provenance':
                        var crd = model.crop;
                        scope.selectedurl = fileUrl(model['provenance_file_id']);
                        scope.disabled = false;
                        scope.coordinates = crd ? [crd.crop_left, crd.crop_top, crd.crop_width + crd.crop_left, crd.crop_height + crd.crop_top] : null;
                        scope.origin = crd ? [crd.origin_left, crd.origin_top] : null;
                        scope.zoom = crd ? crd.origin_zoom : null;
                        break;
                    case 'none':
                        scope.selectedurl = scope.noneurl;
                        scope.disabled = true;
                        scope.coordinates = null;
                        scope.zoom = null;
                        scope.origin = null;
                        // scope.state = null;
                        break;
                    case 'upload':
                        scope.selectedurl = model['file']['content'];
                        scope.disabled = false;
                        scope.coordinates = null;
                        scope.zoom = null;
                        scope.origin = null;
                        // scope.state = null;
                        break;
                    case 'preset':
                        scope.selectedurl = scope.preset_urls[model['preset_id']];
                        scope.disabled = true;
                        scope.coordinates = null;
                        scope.zoom = null;
                        scope.origin = null;
                        // scope.state = null;
                        break;
                    default:
                        console.log('unknown model type');
                        break;
                }

                scope.onload = function (cropper_logic) {
                    if (!do_not_set_ng_crop) {
                        $timeout(function () {
                            scope.prCrop['selected_by_user'] = model;
                        })
                    }
                }

            };

            scope.fileUploaded = function (event) {
                var the_file = (event.target.files && event.target.files.length) ? event.target.files[0] : false;
                $(this).val('');
                if (the_file) {
                    var fr = new FileReader();
                    fr.onload = function (e) {
                        scope.setModel({
                            'type': 'upload',
                            'file': {'mime': the_file.type, 'name': the_file.name, 'content': fr.result}
                        })
                    };
                    fr.onerror = function (e) {
                        add_message('File loading error', 'warning');
                    };
                    fr.readAsDataURL(the_file);
                }
            };

            scope.chooseImage = function (setImage) {
                scope.$root.chooseImageinFileManager("parent." + callback_name, 'choose', '', scope.original_model['browse']);
            };


            scope.zoom_by = function (by, check_only) {
                if (scope.loading || scope.disabled || !scope.logic) return false;
                // console.log(scope.logic, scope.logic.ctr);
                // debugger;
                var ok = false;
                if (by > 1 && scope.zoom <= scope.logic.ctr.max_zoom * 0.99) ok = true;
                if (by < 1 && scope.zoom >= scope.logic.ctr.min_zoom * 1.01) ok = true;
                if (!check_only && ok) $timeout(function () {
                    scope.zoom *= by;
                });
                return ok;
            };

            scope.select_all = function (check_only) {
                if (scope.loading || scope.disabled || !scope.logic) return false;

                if (!check_only) {
                    scope.coordinates = [0, 0, scope.logic.ctr.image_size[0], scope.logic.ctr.image_size[1]];
                }
                return true;
            };


            $(element).append($templateCache.get('pr-crop-buttons.html'));
            $compile(element)(scope);

            // $compile($(element).prev())(scope);
        }
    }
});