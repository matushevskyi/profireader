/**
 * Function calculates difference between two objects/arrays
 * return array or object depending on type of second argument
 * @param {type} a
 * @param {type} b
 * @param {type} notstrict - compare by == if true (if false/ommted by ===)
 * @returns {Array/Object} with elements different in a and b. also if index is present only in one object (a or b)
 * if returened element is array same object are reffered by 'undefined'
 */
function getObjectsDifference(a, b, setval, notstrict) {

    'use strict';

    if ((typeof a !== 'object') || (typeof b !== 'object')) {
        console.log('getObjectsDifference expects both arguments to be array or object');
        return null;
    }

    var ret = $.isArray(b) ? [] : {};

    $.each(a, function (ind, aobj) {
        if ((typeof aobj === 'object') && (typeof b[ind] === 'object')) {
            if ((aobj === null) && (b[ind] === null)) {
                return;
            }
            var nl = getObjectsDifference(aobj, b[ind], setval, notstrict);
            if (!$.isEmptyObject(nl)) {
                ret[ind] = nl;
            }
        }
        else {
            if ((notstrict && (a[ind] == b[ind])) || (!notstrict && (a[ind] === b[ind]))) {
                return;
            }
            ret[ind] = (setval === undefined) ? aobj : setval;
        }
    });
    $.each(b, function (ind, bobj) {
        if ((typeof bobj === 'object') && (typeof a[ind] === 'object')) {

        }
        else {
            if ((notstrict && (a[ind] == b[ind])) || (!notstrict && (a[ind] === b[ind]))) {
                return;
            }
            ret[ind] = (setval === undefined) ? bobj : setval;
        }
    });
    return ret;
}

function quoteattr(s, preserveCR) {
    preserveCR = preserveCR ? '&#13;' : '\n';
    return ('' + s)/* Forces the conversion to string. */
        .replace(/&/g, '&amp;')/* This MUST be the 1st replacement. */
        .replace(/'/g, '&apos;')/* The 4 other predefined entities, required. */
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        /*
         You may add other replacements here for HTML only
         (but it's not necessary).
         Or for XML, only if the named entities are defined in its DTD.
         */
        .replace(/\r\n/g, preserveCR)/* Must be before the next replacement. */
        .replace(/[\r\n]/g, preserveCR);
}


function resolveDictForAngularController(dict) {
    return _.object(_.map(dict, function (val, key) {
        return [key, function () {
            return val
        }]
    }))
}

var prDatePicker_and_DateTimePicker = function (name, $timeout) {
    return {
        require: 'ngModel',
        restrict: 'A',
        scope: {
            ngModel: '=',
        },
        link: function (scope, element, attrs, ngModelController) {

            var defformat = (name === 'prDatePicker') ? 'dddd, LL' : 'dddd, LL (HH:mm)';

            var format = (attrs[name] ? attrs[name] : defformat);
            element.addClass((name === 'prDatePicker') ? "pr-datepicker" : "pr-datetimepicker");

            ngModelController.$formatters = [function (d) {
                var m = moment(d);
                return m.isValid() ? m.format(format) : "";
            }];

            scope.$watch('ngModel', function (newdate, olddate) {
                var setdate = null;
                if (newdate) {
                    setdate = moment(newdate);
                    if (setdate.isValid() && (!olddate) && name === 'prDateTimePicker') {
                        var now = moment();
                        setdate.minutes(now.minutes());
                        setdate.hour(now.hour());
                    }
                }


                element.data("DateTimePicker").date(setdate);
            });

            var opt = {
                locale: window._LANG,
                keepInvalid: true,
                useCurrent: false,
                widgetPositioning: {
                    horizontal: 'left',
                    vertical: 'bottom'
                },
                format: format
            };
            if (name === 'prDateTimePicker') {
                opt['sideBySide'] = true;
            }
            element.datetimepicker(opt).on("dp.change", function (e) {
                $timeout(function () {
                    scope['ngModel'] = e.date ?
                        ((name === 'prDatePicker') ? moment(e.date).format('YYYY-MM-DD') : e.date.toISOString()) :
                        null;
                }, 0)

            })

        }

    }
}

angular.module('profireaderdirectives', ['ui.bootstrap', 'ui.bootstrap.tooltip', 'ui.select'])
    .factory('$publish', ['$http', '$uibModal', function ($http, $uibModal) {
        return function (dict) {
            var modalInstance = $uibModal.open({
                templateUrl: 'submit_publish_dialog.html',
                controller: 'submit_publish_dialog',
                backdrop: 'static',
                keyboard: false,
                resolve: resolveDictForAngularController(dict)
            });
            return modalInstance;
        }
    }])
    .factory('$membership_tags', ['$http', '$uibModal', function ($http, $uibModal) {
        return function (dict) {
            var modalInstance = $uibModal.open({
                templateUrl: 'membership_tags.html',
                controller: 'membership_tags',
                backdrop: 'static',
                keyboard: false,
                resolve: resolveDictForAngularController(dict)
            });
            return modalInstance;
        }
    }])
    .controller('confirm_dialog_controller', function ($scope, $uibModalInstance, title, question, buttons) {

        $scope.buttons = buttons;
        $scope.title = title;
        $scope.question = question;
        $scope.ans = function (resp) {
            if (resp) {
                $uibModalInstance.close(resp)
            }
            else {
                $uibModalInstance.dismiss(resp)
            }
        }

    })
    .factory('$confirm', ['$uibModal', function ($uibModal) {
        return function (title, question, buttons) {
            var modalInstance = $uibModal.open({
                templateUrl: 'confirm.html',
                controller: 'confirm_dialog_controller',
                resolve: {
                    'buttons': function () {
                        return buttons ? buttons : [{'answer': true, 'text': 'Yes', 'class_name': 'btn-default'},
                            {'answer': false, 'text': 'No', 'class_name': 'btn-danger'}];
                    },
                    'title': function () {
                        return title;
                    },
                    'question': function () {
                        return question;
                    }
                }
            });
            return modalInstance.result;
        }

    }])
    .factory('$ok', ['$http', function ($http) {
        return function (url, data, ifok, iferror, translate, disableonsubmid) {
            //console.log($scope);
            function error(result, error_code) {
                if (iferror) {
                    iferror(result, error_code)
                }
                else {
                    // add_message(result, 'danger');
                }
            }

            //TODO MY by OZ: dim disableonsubmid element on submit (by cloning element with coordinates and classes)
            //pass here dialog DOM element from controller wherever $uibModalInstance is used

            return $http.post(url, $.extend({}, data, translate ? {__translate: translate} : {})).then(
                function (resp) {
                    if (!resp || !resp['data'] || typeof resp['data'] !== 'object' || resp === null) {
                        return error('wrong response', -1);
                    }

                    resp = resp ['data'];

                    if (!resp['ok']) {
                        return error(resp['data'], resp['error_code']);
                    }

                    if (ifok) {
                        return ifok(resp['data']);
                    }

                },
                function () {
                    return error('wrong response', -1);
                }
            );
        }
    }])
    // .directive('prSay', ['$controller', '$ok', function ($controller, $ok) {
    //     return {
    //         restrict: 'A',
    //         scope: {
    //             'prSay': '=',
    //         },
    //         link: function (scope, element, attrs) {
    //             var allow_html = ('allow-only-tags' in attrs) ? attrs['allow-only-tags'] : '*';
    //             var phrase = element.html();
    //
    //             if ('watch' in attrs) {
    //                 scope.$watch('prSay', function (nv, ov) {
    //                     if (nv) {
    //                         element.html(pr_dictionary(phrase, [nv], allow_html, scope.$parent, $ok, $controller));
    //                     }
    //                 });
    //             }
    //             else {
    //                 element.html(pr_dictionary(phrase, [scope['prSay']], allow_html, scope.$parent, $ok, $controller));
    //             }
    //
    //         }
    //     }
    // }])
    .directive('prHelpTooltip', ['$compile', '$templateCache', '$controller', function ($compile, $templateCache, $controller) {
        return {
            restrict: 'E',
            link: function (scope, element, attrs) {
                element.html('<span uib-popover-html="\'' + quoteattr(scope.__('help tooltip ' + element.html())) + '\'" ' +
                    'popover-placement="' + (attrs['placement'] ? attrs['placement'] : 'bottom') + '" ' +
                    'popover-trigger="' + (attrs['trigger'] ? attrs['trigger'] : 'mouseenter') + '" ' +
                    'class="' + (attrs['classes'] ? attrs['classes'] : 'glyphicon glyphicon-question-sign') + '"></span>');
                $compile(element.contents())(scope);
            }
        }
    }])
    .directive('prFileChange', function () {
        return {
            restrict: 'A',
            link: function (scope, element, attrs) {
                var onChangeHandler = scope.$eval(attrs.prFileChange);
                element.bind('change', onChangeHandler);
            }
        };
    })
    .directive('prCrop', function ($compile, $templateCache, $timeout) {
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
    })

    .directive('dateTimestampFormat', function () {
        return {
            require: 'ngModel',
            link: function (scope, element, attr, ngModelCtrl) {
                ngModelCtrl.$formatters.unshift(function (timestamp) {
                    if (timestamp) {
                        var date = new Date(timestamp * 1000);
                        return date;
                    } else
                        return "";
                });
                ngModelCtrl.$parsers.push(function (date) {
                    if (date instanceof Date) {
                        var timestamp = Math.floor(date.getTime() / 1000)
                        return timestamp;
                    } else
                        return "";
                });
            }
        };
    })
    .directive('prDateTimePicker', function ($timeout) {
        return prDatePicker_and_DateTimePicker('prDateTimePicker', $timeout);
    }).directive('prDatePicker', function ($timeout) {
    return prDatePicker_and_DateTimePicker('prDatePicker', $timeout);
})
    .directive('prDatepicker', function () {
        return {
            replace: false,
            require: 'ngModel',
            restrict: 'A',
            scope: {
                ngModel: '='
            },
            link: function (scope, element, attrs, model) {
                scope.$watch('ngModel', function (nv, ov) {
                    scope.setdate = scope['ngModel'];
                });
                scope.$watch('setdate', function (nv, ov) {
                    if (nv && nv.setHours) nv.setHours(12);
                    scope['ngModel'] = nv;
                });
            },
            template: function (ele, attrs) {
// TODO: MY BY OZ: please uncoment time (comented by ng-if=0 now), move date and time to one line
                return '<span><input style="width: 15em; display: inline" type="date" class="form-control" uib-datepicker-popup\
               ng-model="setdate" ng-required="true"\
               datepicker-options="dateOptions" close-text="Close"/><span class="input-group-btn"></span>\
               </span>';
            }
        }
    })
    .directive('highlighter', ['$timeout', function ($timeout) {
        return {
            restrict: 'A',
            link: function (scope, element, attrs) {
                scope.$watch(attrs.highlighter, function (nv, ov) {
                    if (nv !== ov) {
                        highlight($(element));
                    }
                });
            }
        };
    }])
    .directive('prImage', [function () {
        return {
            restrict: 'A',
            scope: {
                prImage: '=',
                prNoImage: '@',

            },
            link: function (scope, element, attrs) {
                var image_reference = attrs['prImage'].split('.').pop();
                var no_image = attrs['prNoImage'] ? attrs['prNoImage'] : false;

                if (!no_image) {
                    no_image = noImageForImageName(image_reference);
                }

                scope.$watch('prImage', function (newval, oldval) {
                    element.css({
                        backgroundImage: "url('" + fileUrl(newval, false, no_image) + "')"
                        // backgroundImage: "url('" + newval + "')"
                    });
                });
                element.attr('src', static_address('images/0.gif'));
                element.addClass('bg-contain');
            }
        };
    }]).directive('prImageWatch', [function () {
    return {
        restrict: 'A',
        scope: {
            prImageWatch: '=',
            prNoImage: '@',

        },
        link: function (scope, element, attrs) {
            var image_reference = attrs['prImageWatch'].split('.').pop();
            var no_image = attrs['prNoImage'] ? attrs['prNoImage'] : false;

            if (!no_image) {
                no_image = noImageForImageName(image_reference);
            }

            scope.$watch('prImageWatch', function (newval, oldval) {
                element.css({
                    backgroundImage: "url('" + fileUrl(newval, false, no_image) + "')"
                });
            });
            element.attr('src', static_address('images/0.gif'));
            element.addClass('bg-contain');
        }
    };
}])
    .directive('prImageUrl', [function () {
        return {
            restrict: 'A',
            scope: false,
            link: function (scope, element, attrs) {
                element.attr('src', static_address('images/0.gif'));
                element.css({
                    backgroundPosition: attrs['prImagePosition'] ? attrs['prImagePosition'] : 'center',
                    backgroundImage: 'url(' + attrs['prImageUrl'] + ')'
                });
                element.addClass('bg-contain');
            }
        };
    }]).directive('prImageUrlWatch', [function () {
    return {
        restrict: 'A',
        scope: {
            prImageUrlWatch: '=',
        },
        link: function (scope, element, attrs) {
            element.attr('src', static_address('images/0.gif'));
            element.addClass('bg-contain');
            scope.$watch('prImageUrlWatch', function (newval, oldval) {
                if (newval)
                    element.css({
                        backgroundPosition: attrs['prImagePosition'] ? attrs['prImagePosition'] : 'center',
                        backgroundImage: "url('" + newval + "')"
                    });
            });
        }
    };
}])
//TODO: SS by OZ: better use actions (prUserCan) not rights. action can depend on many rights
    .directive('prUserRights', function ($timeout) {
        return {
            restrict: 'AE',
            link: function (scope, element, attrs) {
                var elementType = element.prop('nodeName');
                scope.$watch(attrs['prUserRights'], function (val) {
                    disable(val)
                })

                var disable = function (allow) {
                    if (allow === false) {
                        if (elementType === 'BUTTON' || elementType === 'INPUT') {
                            element.prop('disabled', true)
                        } else if (elementType === 'A') {
                            element.css({'pointer-events': 'none', 'cursor': 'default'})
                        } else {
                            element.hide()
                        }
                    }
                }
            }
        };
    })
    .directive('prUserCan', function ($timeout) {
        return {
            restrict: 'AE',
            link: function (scope, element, attrs) {
                var elementType = element.prop('nodeName');
                var enable = function (allow) {
                    if (allow === true) {
                        element.prop('disabled', false);
                        element.removeClass('disabled');
                        element.prop('title', '');
                    } else {
                        if (elementType === 'BUTTON' || elementType === 'INPUT') {
                            element.prop('disabled', true);
                            element.prop('title', allow === false ? '' : allow);
                        } else if (elementType === 'A') {
                            element.addClass('disabled');
                            element.prop('title', allow === false ? '' : allow);
                        } else {
                            element.hide()
                        }

                    }
                }

                scope.$watch(attrs['prUserCan'], function (val) {
                    enable(val)
                })


            }
        };
    })
    .service('objectTransformation', function () {
        var objectTransformation = {};

        objectTransformation.reverseKeyValue = function (objIn) {
            var objOut = {}, keys, i;
            keys = Object.keys($scope.data.PortalDivisionTags3);
            for (i = 0; i < objIn.length; i++) {
                objOut[objIn[keys[i]]] = keys[i];
            }
            return objOut;
        };

        objectTransformation.getValues1 = function (objList, key, unique) {
            var values = [], value;
            for (var i = 0; i < objList.length; i++) {
                value = objList[i][key];
                if (!unique || (values.indexOf(value) === -1)) {
                    values.push(value);
                }
            }
            return values;
        };

        objectTransformation.getValues2 = function (objList, key1, key2) {
            var resultObject = {}, key, value;
            for (var i = 0; i < objList.length; i++) {
                key = objList[i][key1];
                value = objList[i][key2];

                if (typeof resultObject[key] === 'undefined') {
                    resultObject[key] = [value]
                } else {
                    if (resultObject[key].indexOf(value) === -1) {
                        resultObject[key].push(value)
                    }
                }
            }
            return resultObject;
        };

        objectTransformation.getValues3 = function (objList, key1, key2, key2List) {
            var resultObject = {}, key, i, objFilledWithFalse = {};

            for (i = 0; i < key2List.length; i++) {
                objFilledWithFalse[key2List[i]] = false
            }

            for (i = 0; i < objList.length; i++) {
                key = objList[i][key1];
                if (typeof resultObject[key] === 'undefined') {
                    resultObject[key] = $.extend(true, {}, objFilledWithFalse);
                }
                resultObject[key][objList[i][key2]] = true;
            }

            return resultObject;
        };

        objectTransformation.getValues4 = function (objList, key1, key2, key2List) {
            var resultObject = {}, key, i, objFilledWithFalse = {}, lList, elem;

            lList = [];
            for (i = 0; i < objList.length; i++) {
                elem = objList[i][key1];
                if (lList.indexOf(elem) === -1) {
                    lList.push(elem);
                }
            }

            for (i = 0; i < lList.length; i++) {
                objFilledWithFalse[lList[i]] = false;
            }

            for (i = 0; i < key2List.length; i++) {
                resultObject[key2List[i]] = $.extend(true, {}, objFilledWithFalse);
            }

            for (i = 0; i < objList.length; i++) {
                key = objList[i];
                resultObject[key[key2]][key[key1]] = true;
            }

            return resultObject;
        };

        // substitution in keys is performed
        objectTransformation.subsInKey = function (objIn, objForSubstitution) {
            var keys, i, objOut;

            keys = Object.keys(objIn);
            objOut = {};

            for (i = 0; i < keys.length; i++) {
                objOut[objForSubstitution[keys[i]]] = objIn[keys[i]];
            }

            return objOut;
        };

        // substitution of list elements is performed
        objectTransformation.subsElemOfList = function (listIn, objForSubstitution) {
            var i, listOut;
            listOut = [];
            for (i = 0; i < listIn.length; i++) {
                listOut.push(objForSubstitution[listIn[i]])
            }
            return listOut;
        };

        return objectTransformation;
    }).filter('propsFilter', function () {
    return function (items, props) {
        var out = [];

        if (angular.isArray(items)) {
            var keys = Object.keys(props);

            items.forEach(function (item) {
                var itemMatches = false;

                for (var i = 0; i < keys.length; i++) {
                    var prop = keys[i];
                    var text = props[prop].toLowerCase();
                    if (item[prop].toString().toLowerCase().indexOf(text) !== -1) {
                        itemMatches = true;
                        break;
                    }
                }

                if (itemMatches) {
                    out.push(item);
                }
            });
        } else {
            // Let the output be the input untouched
            out = items;
        }

        return out;
    };
}).filter('html', ['$sce', function($sce){
        return function(text) {
            return $sce.trustAsHtml(text);
        };
    }]);


areAllEmpty = function () {
    var are = true;

    $.each(arguments, function (ind, object) {
        if (are) {
            var ret = true;
            if ($.isArray(object)) {
                ret = object.length ? false : true;
            }
            else if ($.isPlainObject(object) && $.isEmptyObject(object)) {
                ret = true;
            }
            else {
                ret = ((object === undefined || object === false || object === null || object === 0) ? true : false);
            }
            are = ret;
        }
    });
    return are;
};


function file_choose(selectedfile) {
    console.log(selectedfile)
    var args = top.tinymce.activeEditor.windowManager.getParams();
    var win = (args.window);
    var input = (args.input);
    if (selectedfile['type'] === 'file_video') {
        win.document.getElementById(input).value = "https://youtu.be/" + selectedfile['youtube_data']['id'] + "?list=" + selectedfile['youtube_data']['playlist_id'];
    } else {
        win.document.getElementById(input).value = selectedfile['file_url'];
    }
    top.tinymce.activeEditor.windowManager.close();
}

// 'ui.select' uses static_address('js/select.js') included in _index_layout.html
//module = angular.module('Profireader', ['ui.bootstrap', 'profireaderdirectives', 'ui.tinymce', 'ngSanitize', 'ui.select']);

module = angular.module('Profireader', pr_angular_modules);

module.config(function ($provide) {
    $provide.decorator('$controller', function ($delegate) {
        return function (constructor, locals, later, indent) {
            if (typeof constructor === 'string' && !locals.$scope.controllerName) {
                locals.$scope.controllerName = constructor;
            }
            return $delegate(constructor, locals, later, indent);
        };
    });
})

Date.prototype.toISOString = function () {
    //console.log('Tue, 26 Jan 2016 13:59:14 GMT', this.toUTCString());
    return this.toUTCString();
    //dateFormat(this, "dddd, mmmm dS, yyyy, h:MM:ss TT");
    //  return 'here goes my awesome formatting of Date Objects '+ this;
};
//    .config(function($httpProvider) {
//    $httpProvider.defaults.transformRequest.unshift(function (data) {
//        console.log(data);
//        return data;
//    })
//});


module.controller('filemanagerCtrl', ['$scope', '$uibModalInstance', 'file_manager_called_for', 'file_manager_on_action',
    'file_manager_default_action', 'get_root',
    function ($scope, $uibModalInstance, file_manager_called_for, file_manager_on_action, file_manager_default_action, get_root) {

//TODO: SW fix this pls

        closeFileManager = function () {
            $scope.$apply(function () {
                $uibModalInstance.dismiss('cancel')
            });
        };

        $scope.close = function () {
            $uibModalInstance.dismiss('cancel');
        };
        $scope.src = '/filemanager/';
        var params = {};
        if (file_manager_called_for) {
            params['file_manager_called_for'] = file_manager_called_for;
        }
        if (file_manager_on_action) {
            params['file_manager_on_action'] = angular.toJson(file_manager_on_action);
        }

        if (file_manager_default_action) {
            params['file_manager_default_action'] = file_manager_default_action;
        }
        if (get_root) {
            params['get_root'] = get_root;
        }
        $scope.src = $scope.src + '?' + $.param(params);
    }]);

module.directive('ngEnter', function () {
    return function (scope, element, attrs) {
        element.bind("keydown keypress", function (event) {
            if (event.which === 13) {
                scope.$apply(function () {
                    scope.$eval(attrs.ngEnter, {'event': event});
                });

                event.preventDefault();
            }
        });
    };
});
module.directive('ngDropdownMultiselect', ['$filter', '$document', '$compile', '$parse', '$timeout', '$ok',
    function ($filter, $document, $compile, $parse, $timeout, $ok) {

        return {
            restrict: 'AE',
            scope: {
                addData: '=',
                data: '=',
                send: '=',
                parentScope: '=',
                selectedModel: '=',
                options: '=',
                extraSettings: '=',
                events: '=',
                searchFilter: '=?',
                translationTexts: '=',
                groupBy: '@'
            },
            template: function (element, attrs) {
                var checkboxes = attrs.checkboxes ? true : false;
                var groups = attrs.groupBy ? true : false;

                var template = '<div class="multiselect-parent btn-group dropdown-multiselect" style="width:100%"><div class="kk"><div>';
                template += '<button type="button" style="width:100%"  id="t1" class="dropdown-toggle" ng-class="settings.buttonClasses" ng-disabled="parentScope.loading" ng-click="toggleDropdown()">{{getButtonText()}}&nbsp;<span class="caret"></span></button>';
                template += '<ul class="dropdown-menu dropdown-menu-form ng-dr-ms" ng-style="{display: open ? \'block\' : \'none\', height : settings.scrollable ? settings.scrollableHeight : \'auto\' }" style="position: fixed; top:auto; left: auto; width: 20%;cursor: pointer" >';
                template += '<li ng-show="settings.selectionLimit === 0"><a data-ng-click="selectAll()"><span class="glyphicon glyphicon-ok"></span>  {{texts.checkAll}}</a>';
                template += '<li ng-show="settings.showUncheckAll"><a data-ng-click="deselectAll(true);"><span class="glyphicon glyphicon-remove"></span>   {{texts.uncheckAll}}</a></li>';
                template += '<li ng-show="(settings.showCheckAll || settings.selectionLimit < 0) && !settings.showUncheckAll" class="divider"></li>';
                template += '<li ng-show="settings.enableSearch"><div class="dropdown-header"><input type="text" class="form-control" style="width: 100%;" ng-model="searchFilter" placeholder="{{texts.searchPlaceholder}}" /></li>';
                template += '<li ng-show="settings.enableSearch" class="divider"></li>';
                if (groups) {
                    template += '<li ng-repeat-start="option in orderedItems | filter: searchFilter" ng-show="getPropertyForObject(option, settings.groupBy) !== getPropertyForObject(orderedItems[$index - 1], settings.groupBy)" role="presentation" class="dropdown-header">{{ getGroupTitle(getPropertyForObject(option, settings.groupBy)) }}</li>';
                    template += '<li ng-repeat-end role="presentation">';
                } else {
                    template += '<li role="presentation" ng-repeat="option in options | filter: searchFilter">';
                }
                template += '<a role="menuitem" tabindex="-1" ng-click="setSelectedItem(getPropertyForObject(option,settings.idProp) , getPropertyForObject(option,settings.displayProp))">';
                if (checkboxes) {
                    template += '<div class="checkbox"><label><input class="checkboxInput" type="checkbox" ng-click="checkboxClick($event, getPropertyForObject(option,settings.idProp))" ng-checked="isChecked(getPropertyForObject(option,settings.idProp), getPropertyForObject(option,settings.displayProp))" /> {{getPropertyForObject(option, settings.displayProp)}}</label></div></a>';
                } else {
                    template += '<span data-ng-class="{\'glyphicon glyphicon-check\': isChecked(getPropertyForObject(option,settings.idProp), getPropertyForObject(option,settings.displayProp)), \'glyphicon glyphicon-unchecked\': !isChecked(getPropertyForObject(option,settings.idProp), getPropertyForObject(option,settings.displayProp))}"></span> {{getPropertyForObject(option, settings.displayProp)}}</a>';
                }
                template += '</li>';
                template += '<li role="presentation" ng-show="settings.selectionLimit > 1"><a role="menuitem">{{selectedModel.length}} {{texts.selectionOf}} {{settings.selectionLimit}} {{texts.selectionCount}}</a></li>';
                template += '</ul>';
                template += '</div>';

                element.html(template);
            },
            link: function ($scope, $element, $attrs) {
                var $dropdownTrigger = $element.children()[0];

                $scope.toggleDropdown = function () {
                    $scope.open = !$scope.open;
                };

                $scope.checkboxClick = function ($event, id) {
                    $scope.setSelectedItem(id);
                    $event.stopImmediatePropagation();
                };

                $scope.externalEvents = {
                    onItemSelect: angular.noop,
                    onItemDeselect: angular.noop,
                    onSelectAll: angular.noop,
                    onDeselectAll: angular.noop,
                    onInitDone: angular.noop,
                    onMaxSelectionReached: angular.noop
                };

                $scope.settings = {
                    dynamicTitle: true,
                    scrollable: false,
                    scrollableHeight: '300px',
                    closeOnBlur: true,
                    displayProp: 'label',
                    idProp: 'value',
                    externalIdProp: 'value',
                    enableSearch: false,
                    selectionLimit: $scope.addData.limit ? $scope.addData.limit : 0,
                    showCheckAll: true,
                    showUncheckAll: true,
                    closeOnSelect: false,
                    buttonClasses: 'btn btn-default ',
                    closeOnDeselect: false,
                    groupBy: $attrs.groupBy || undefined,
                    groupByTextProvider: null,
                    smartButtonMaxItems: 0,
                    smartButtonTextConverter: angular.noop
                };

                $scope.translate_phrase = function () {
                    $scope.$$translate = $scope.parentScope.$$translate;
                    var args = [].slice.call(arguments);
                    return pr_dictionary(args.shift(), args, '', $scope, $ok, $scope.parentScope.controllerName)
                };

                $scope.texts = {
                    checkAll: $scope.translate_phrase("Check All"),
                    uncheckAll: $scope.translate_phrase('Uncheck All'),
                    selectionCount: $scope.translate_phrase('checked'),
                    selectionOf: '/',
                    searchPlaceholder: $scope.translate_phrase('Search...'),
                    buttonDefaultText: $scope.translate_phrase('Select'),
                    dynamicButtonTextSuffix: $scope.translate_phrase('checked')
                };

                $scope.searchFilter = $scope.searchFilter || '';

                if (angular.isDefined($scope.settings.groupBy)) {
                    $scope.$watch('options', function (newValue) {
                        if (angular.isDefined(newValue)) {
                            $scope.orderedItems = $filter('orderBy')(newValue, $scope.settings.groupBy);
                        }
                    });
                }

                angular.extend($scope.settings, $scope.extraSettings || []);
                angular.extend($scope.externalEvents, $scope.events || []);
                angular.extend($scope.texts, $scope.translationTexts);

                $scope.singleSelection = $scope.settings.selectionLimit === 1;

                function getFindObj(id) {
                    var findObj = {};

                    if ($scope.settings.externalIdProp === '') {
                        findObj[$scope.settings.idProp] = id;
                    } else {
                        findObj[$scope.settings.externalIdProp] = id;
                    }

                    return findObj;
                }

                function clearObject(object) {
                    for (var prop in object) {
                        delete object[prop];
                    }
                }

                if ($scope.singleSelection) {
                    if (angular.isArray($scope.selectedModel) && $scope.selectedModel.length === 0) {
                        clearObject($scope.selectedModel);
                    }
                }

                if ($scope.settings.closeOnBlur) {
                    $document.on('click', function (e) {
                        var target = e.target.parentElement;
                        var parentFound = false;

                        while (angular.isDefined(target) && target !== null && !parentFound) {
                            if (_.contains(target.className.split(' '), 'multiselect-parent') && !parentFound) {
                                if (target === $dropdownTrigger) {
                                    parentFound = true;
                                }
                            }
                            target = target.parentElement;
                        }

                        if (!parentFound) {
                            $scope.$apply(function () {
                                $scope.open = false;
                            });
                        }
                    });
                }

                $scope.getGroupTitle = function (groupValue) {
                    if ($scope.settings.groupByTextProvider !== null) {
                        return $scope.settings.groupByTextProvider(groupValue);
                    }

                    return groupValue;
                };

                $scope.get_default_selected = function (exeptions) {
                    if (exeptions) {
                        $scope.listElemens[$scope.addData.field] = [];
                        $timeout(function () {
                            for (var f = 0; f < $scope.options.length; f++) {
                                if (exeptions instanceof Array) {
                                    if (exeptions.indexOf($scope.options[f]['label']) === -1) {
                                        $scope.listElemens[$scope.addData.field].push($scope.options[f]['label'])
                                    }
                                } else {
                                    if ($scope.options[f]['label'] !== exeptions) {
                                        $scope.listElemens[$scope.addData.field].push($scope.options[f]['label'])
                                    }
                                }
                            }
                        }, 500)
                    }
                };

                $scope.getButtonText = function () {
                    if (!$scope.listElemens) {
                        $scope.listElemens = {};
                        $scope.listElemens[$scope.addData.field] = [];
                        $timeout(function () {
                            $scope.filters_exception = $scope.parentScope.gridApi.grid.filters_init_exception
                            if ($scope.filters_exception) {
                                $scope.get_default_selected($scope.filters_exception)
                            }
                        }, 2000);

                    }
                    if ($scope.settings.dynamicTitle && ($scope.selectedModel.length > 0 || (angular.isObject($scope.selectedModel) && _.keys($scope.selectedModel).length > 0))) {
                        if ($scope.settings.smartButtonMaxItems > 0) {
                            var itemsText = [];
                            angular.forEach($scope.options, function (optionItem) {
                                if ($scope.isChecked($scope.getPropertyForObject(optionItem, $scope.settings.idProp))) {
                                    var displayText = $scope.getPropertyForObject(optionItem, $scope.settings.displayProp);
                                    var converterResponse = $scope.settings.smartButtonTextConverter(displayText, optionItem);
                                    itemsText.push(converterResponse ? converterResponse : displayText);
                                }
                            });

                            if ($scope.selectedModel.length > $scope.settings.smartButtonMaxItems) {
                                itemsText = itemsText.slice(0, $scope.settings.smartButtonMaxItems);
                                itemsText.push('...');
                            }

                            return itemsText.join(', ');
                        } else {
                            var totalSelected;
                            if ($scope.singleSelection) {
                                totalSelected = ($scope.selectedModel !== null && angular.isDefined($scope.selectedModel[$scope.settings.idProp])) ? 1 : 0;
                            } else {
                                totalSelected = angular.isDefined($scope.selectedModel) ? $scope.listElemens[$scope.addData.field].length : 0;
                            }

                            if (totalSelected === 0) {
                                return $scope.texts.buttonDefaultText;
                            } else {
                                return totalSelected + ' ' + $scope.texts.dynamicButtonTextSuffix;
                            }
                        }
                    } else {
                        return $scope.texts.buttonDefaultText;
                    }
                };

                $scope.getPropertyForObject = function (object, property) {
                    if (angular.isDefined(object) && object.hasOwnProperty(property)) {
                        return object[property];
                    }
                    return '';
                };

                $scope.selectAll = function () {
                    $scope.isSelectAll = true;
                    if ($scope.options.length !== $scope.listElemens[$scope.addData.field].length) {
                        $scope.externalEvents.onSelectAll();
                        $scope.listElemens[$scope.addData.field] = [];
                        angular.forEach($scope.options, function (value) {
                            $scope.setSelectedItem(value[$scope.settings.idProp], '', true);
                        });
                        for (var f = 0; f < $scope.options.length; f++) {
                            $scope.listElemens[$scope.addData.field].push($scope.options[f]['label'])
                        }
                        $scope.data.filter[$scope.addData.field] = $scope.listElemens[$scope.addData.field];
                        $scope.send($scope.data)
                    }
                };

                $scope.deselectAll = function (sendEvent) {
                    if (sendEvent && $scope.listElemens[$scope.addData.field].length > 0) {
                        $scope.isSelectAll = false;
                        delete $scope.data.filter[$scope.addData.field];
                        $scope.listElemens[$scope.addData.field] = [];
                        if ($scope.filters_exception)
                            $scope.data.filter[$scope.addData.field] = []
                        $scope.send($scope.data);
                        if ($scope.singleSelection) {
                            clearObject($scope.selectedModel);
                        } else {
                            $scope.selectedModel.splice(0, $scope.selectedModel.length);
                        }
                    }
                };

                $scope.setSelectedItem = function (id, label, dontRemove) {
                    var findObj = getFindObj(id);
                    var finalObj = null;
                    if ($scope.settings.externalIdProp === '') {
                        finalObj = _.find($scope.options, findObj);
                    } else {
                        finalObj = findObj;
                    }
                    if ($scope.singleSelection) {
                        clearObject($scope.selectedModel);
                        angular.extend($scope.selectedModel, finalObj);
                        $scope.externalEvents.onItemSelect(finalObj);
                        $scope.listElemens[$scope.addData.field].push(label);
                        $scope.data.filter[$scope.addData.field] = $scope.listElemens[$scope.addData.field];
                        $scope.send($scope.data);
                        if ($scope.settings.closeOnSelect) $scope.open = false;

                        return;
                    }

                    dontRemove = dontRemove || false;
                    var exists = $scope.listElemens[$scope.addData.field].indexOf(label) !== -1;

                    if (!dontRemove && exists) {
                        $scope.externalEvents.onItemDeselect(findObj);
                        $scope.isSelectAll = false;
                        index = $scope.listElemens[$scope.addData.field].indexOf(label);
                        $scope.listElemens[$scope.addData.field].splice(index, 1);
                        if ($scope.listElemens[$scope.addData.field].length > 0) {
                            $scope.data.filter[$scope.addData.field] = $scope.listElemens[$scope.addData.field];
                        } else {
                            delete $scope.data.filter[$scope.addData.field];
                        }
                        $scope.send($scope.data)
                    } else if (!exists && ($scope.settings.selectionLimit === 0 || $scope.listElemens[$scope.addData.field].length < $scope.settings.selectionLimit)) {
                        $scope.externalEvents.onItemSelect(finalObj);
                        if (label.length > 0) {
                            $scope.listElemens[$scope.addData.field].push(label);
                            $scope.data.filter[$scope.addData.field] = $scope.listElemens[$scope.addData.field];
                            $scope.send($scope.data)
                        }
                    }
                    if ($scope.settings.closeOnSelect) $scope.open = false;
                };

                $scope.isChecked = function (id, label) {
                    if ($scope.singleSelection) {
                        return $scope.selectedModel !== null && angular.isDefined($scope.selectedModel[$scope.settings.idProp]) && $scope.selectedModel[$scope.settings.idProp] === getFindObj(id)[$scope.settings.idProp];
                    }
                    if ($scope.isSelectAll) {
                        return true
                    }
                    return $scope.listElemens[$scope.addData.field].indexOf(label) !== -1;
                };

                $scope.externalEvents.onInitDone();
            }
        };
    }]);

function now() {
    return Date.now() / 1000;
}

function pr_dictionary(phrase, dictionaries, allow_html, scope, $ok, ctrl) {
    allow_html = allow_html ? allow_html : '';
    if (typeof phrase !== 'string') {
        return '';
    }
    // if (!scope.$$translate) {
    //     scope.$$translate = {};
    // }
    //console.log(scope.$$translate)

    var t = now();
    //TODO OZ by OZ hasOwnProperty
    phrase = phrase.replace('\n', ' ').replace(/[\s]+/gi, ' ').trim();

    var CtrlName = scope.controllerName ? scope.controllerName : ctrl;
    var phrase_dict;

    if (!scope.$$translate || !scope.$$translate[phrase]) {
        phrase_dict = {'lang': phrase, 'time': t, allow_html: allow_html}
    }

    if (scope.$$translate) {
        if (!scope.$$translate[phrase]) {
            scope.$$translate[phrase] = phrase_dict;
            $ok('/tools/save_translate/', {
                template: CtrlName,
                phrase: phrase,
                allow_html: allow_html,
                url: window.location.href
            }, function (resp) {

            });
        }
        else {
            phrase_dict = scope.$$translate[phrase];
        }
    }

    if ((t - phrase_dict['time']) > 86400) {
        phrase_dict['time'] = t;
        $ok('/tools/update_last_accessed/', {template: CtrlName, phrase: phrase}, function (resp) {
        });
    }

    if (phrase_dict['allow_html'] !== allow_html) {
        phrase_dict['allow_html'] = allow_html;
        $ok('/tools/change_allowed_html/', {
            template: CtrlName,
            phrase: phrase,
            allow_html: allow_html
        }, function (resp) {
        });
    }


    if (!dictionaries.length) {
        dictionaries = [true];
    }

    var ret = phrase_dict['lang'];
    ret = ret.replace(/%\(([^)]*)\)(s|d|f|m|i)/g, function (g0, g1) {
        var indexes = g1.split('.');
        var d = {};
        try {
            $.each(dictionaries, function (ind, dict) {
                $.extend(d, dict === true ? scope : dict);
            });

            for (var i in indexes) {
                if (typeof d[indexes[i]] !== 'undefined') {
                    d = d[indexes[i]];
                }
                else {
                    return g1;
                }
            }
            return d;
        }
        catch (a) {
            console.log(g0, g1);
            return g1
        }
    });
    return ret;
}

module.run(function ($rootScope, $ok, $sce, $uibModal, $sanitize, $timeout, $templateCache) {
    //$rootScope.theme = 'bs3'; // bootstrap3 theme. Can be also 'bs2', 'default'
    angular.extend($rootScope, {
        fileUrl: function (file_id, down, if_no_file) {
            return fileUrl(file_id, down, if_no_file);
        },
        highlightSearchResults: function (full_text, search_text) {
            if (search_text !== '' && search_text !== undefined) {
                var re = new RegExp(search_text, "g");
                return $sce.trustAsHtml(full_text.replace(re, '<span style="color:blue">' + search_text + '</span>'));
            }
            return $sce.trustAsHtml(full_text);
        },
        __: function () {
            var args = [].slice.call(arguments);
            return $sce.trustAsHtml(pr_dictionary(args.shift(), args, '*', this, $ok));
        },
        _: function () {
            // debugger;
            var args = [].slice.call(arguments);
            return pr_dictionary(args.shift(), args, '', this, $ok);
        },
        moment: function (value, out_format) {
            return moment.utc(value).local().format(out_format ? out_format : 'dddd, LL (HH:mm)', value)
        },
        MAIN_DOMAIN: MAIN_DOMAIN,
        static_address: function (relative_file_name) {
            return static_address(relative_file_name);
        },
        highlight: function (text, search) {
            if (!search) {
                return $sce.trustAsHtml(text);
            }
            return $sce.trustAsHtml(text.replace(new RegExp(search, 'gi'), '<span class="ui-select-highlight">$&</span>'));
        },

        loadData: function (url, senddata, beforeload, afterload) {
            var scope = this;
            scope.loading = true;
            $ok(url ? url : '', senddata ? senddata : {}, function (data) {
                if (!beforeload) beforeload = function (d) {
                    return d;
                };
                scope.data = beforeload(data);
                scope.original_data = $.extend(true, {}, scope.data);
                if (afterload) afterload();

            }).finally(function () {
                scope.loading = false;
            });
        },
        areAllEmpty: areAllEmpty,
        chooseImageinFileManager: function (do_on_action, default_action, callfor, id) {
            var scope = this;
            var callfor_ = callfor ? callfor : 'file_browse_image';
            var default_action_ = default_action ? default_action : 'file_browse_image';
            var root_id = id ? id : '';
            scope.filemanagerModal = $uibModal.open({
                templateUrl: 'filemanager.html',
                controller: 'filemanagerCtrl',
                size: 'filemanager-halfscreen',
                resolve: {
                    file_manager_called_for: function () {
                        return callfor_
                    },
                    file_manager_on_action: function () {
                        return {
                            choose: do_on_action
                        }
                    },
                    file_manager_default_action: function () {
                        return default_action_
                    },
                    get_root: function () {
                        return root_id
                    }
                }
            });
        },
        loadNextPage: function (url, after_load) {
            var lnpf = function (onscroll) {
                var atend = onscroll ?
                    ($(window).scrollTop() >= $(document).height() - $(window).height() - 10) :
                    (($(document).height() - $(window).height() === 0));
                if (atend && !scope.loading && !scope.data.end) {
                    scope.next_page += 1;
                    scope.loading = true;
                    load();
                }
            }
            var scope = this;
            scope.next_page = 1;
            $(window).scroll(function () {
                if (scope.scroll_data) {
                    scope.scroll_data.next_page = scope.next_page
                }
                lnpf(true);
            });

            $timeout(lnpf, 500);
            var load = function () {
                $ok(url, scope.scroll_data ? scope.scroll_data : {next_page: scope.next_page}, function (resp) {
                    scope.data.end = resp.end;
                    after_load(resp);
                    scope.loading = false;
                }).finally(function () {
                    $timeout(function () {
                        lnpf();
                    }, 1000)
                });
            }
        },
        dateOptions: {
            formatYear: 'yy',
            startingDay: 1
        },
        tinymceImageOptions: {
            inline: false,
            menu: [],
            width: 750,
            plugins: 'advlist autolink link image charmap print paste table media',
            skin: 'lightgray',
            theme: 'modern',
            'toolbar1': "undo redo | bold italic | alignleft aligncenter alignright alignjustify | styleselect | bullist numlist outdent indent | media link image table",
            //'toolbar1': "undo redo | bold italic | alignleft aligncenter alignright alignjustify | styleselect | bullist numlist outdent indent | link image table"[*],
            'valid_elements': "iframe[*],img[*],table[*],tbody[*],td[*],th[*],tr[*],p[*],h1[*],h2[*],h3[*],h4[*],h5[*],h6[*],div[*],ul[*],ol[*],li[*],strong/b[*],em/i[*],span[*],blockquote[*],sup[*],sub[*],code[*],pre[*],a[*]",
            //init_instance_callback1: function () {
            //    console.log('init_instance_callback', arguments);
            //},
            file_browser_callback: function (field_name, url, type, win) {
                var cmsURL = '/filemanager/?file_manager_called_for=file_browse_' + type +
                    '&file_manager_default_action=choose&file_manager_on_action=' + encodeURIComponent(angular.toJson({choose: 'parent.file_choose'}));
                tinymce.activeEditor.windowManager.open({
                        file: cmsURL,
                        width: 950,  // Your dimensions may differ - toy around with them!
                        height: 700,
                        resizable: "yes",
                        //inline: "yes",  // This parameter only has an effect if you use the inlinepopups plugin!
                        close_previous: "yes"
                    }
                    ,
                    {
                        window: win,
                        input: field_name
                    }
                )
                ;

            },
            //valid_elements: Config['article_html_valid_elements'],
            //valid_elements: 'a[class],img[class|width|height],p[class],table[class|width|height],th[class|width|height],tr[class],td[class|width|height],span[class],div[class],ul[class],ol[class],li[class]',
            //TODO: OZ by OZ: select css for current theme. also look for another place with same todo
            content_css: [static_address('front/css/bootstrap.css'), static_address('css/article.css'), static_address('front/bird/css/article.css')],


            //paste_auto_cleanup_on_paste : true,
            //paste_remove_styles: true,
            //paste_remove_styles_if_webkit: true,
            //paste_strip_class_attributes: "all'),

            //style_formats: [
            //    {title: 'Bold text', inline: 'b'},
            //    {title: 'Red text', inline: 'span', styles: {color: '#ff0000'}},
            //    {title: 'Red header', block: 'h1', styles: {color: '#ff0000'}},
            //
            //    {
            //        title: 'Image Left',
            //        selector: 'img',
            //        styles: {
            //            'float': 'left',
            //            'margin': '0 10px 0 10px'
            //        }
            //    },
            //    {
            //        title: 'Image Right',
            //        selector: 'img',
            //        styles: {
            //            'float': 'right',
            //            'margin': '0 0 10px 10px'
            //        }
            //    }
            //]

        }
    })
});


function cleanup_html(html) {
    normaltags = '^(span|a|br|div|table)$';
    common_attributes = {
        whattr: {'^(width|height)$': '^([\d]+(.[\d]*)?)(em|px|%)$'}
    };

    allowed_tags = {
        '^table$': {allow: '^(tr)$', attributes: {whattr: true}},
        '^tr$': {allow: '^(td|th)$', attributes: {}},
        '^td$': {allow: normaltags, attributes: {whattr: true}},
        '^a$': {allow: '^(span)$', attrсibutes: {'^href$': '.*'}},
        '^img$': {allow: false, attributes: {'^src$': '.*'}},
        '^br$': {allow: false, attributes: {}},
        '^div$': {allow: normaltags, attributes: {}}
    };

    $.each(allowed_tags, function (tag, properties) {
        var attributes = properties.attributes ? properties.attributes : {}
        $.each(attributes, function (attrname, allowedvalus) {
            if (allowedvalus === true) {
                allowed_tags[tag].attributes[attrname] = common_attributes[attrname] ? common_attributes[attrname] : '.*';
            }
        });
    });

    var tags = html.split(/<[^>]*>/);

    $.each(tags, function (tagindex, tag) {
        console.log(tagindex, tag);
    });

    return html;
}


None = null;
False = false;
True = true;

$.fn.scrollTo = function () {
    return this.each(function () {
        $('html, body').animate({
            scrollTop: $(this).offset().top
        }, 1000);
    });
};

function scrool($el) {
    $($el).scrollTo();
}

function highlight($el) {
    $($el).addClass('highlight');
    setTimeout(function () {
        $($el).removeClass('highlight');
    }, 35000);
};


function angularControllerFunction(controller_attr, function_name) {
    var nothing = function () {
    };
    var el = $('[ng-controller=' + controller_attr + ']');
    if (!el && !el.length) return nothing;
    if (!angular.element(el[0])) return nothing;
    if (!angular.element(el[0]).scope()) return nothing;
    if (!angular.element(el[0]).scope()) return nothing;
    var func = angular.element(el[0]).scope()[function_name];
    var controller = angular.element(el[0]).controller();
    return (func && controller) ? func : nothing;
}

function fileUrl(id, down, if_no_file) {

    if (!id) return (if_no_file ? if_no_file : '');

    if (!id.match(/^[^-]*-[^-]*-4([^-]*)-.*$/, "$1")) return (if_no_file ? if_no_file : '');

    var server = id.replace(/^[^-]*-[^-]*-4([^-]*)-.*$/, "$1");
    if (down) {
        return '//file' + server + '.' + MAIN_DOMAIN + '/' + id + '?d'
    } else {
        return '//file' + server + '.' + MAIN_DOMAIN + '/' + id + '/'
    }
}

function cloneObject(o) {
    return (o === null || typeof o !== 'object') ? o : $.extend(true, {}, o);
}

function add_message(amessage, atype, atime, aunique_id) {
    return angularControllerFunction('message-controller', 'add_message')(amessage, atype, atime, aunique_id);
}


function getLengthOfAssociativeArray(array) {
    return Object.keys(array).length
}

function randomHash() {
    var text = "";
    var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (var i = 0; i < 32; i++)
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    return text;
}

function buildAllowedTagsAndAttributes() {

    var class_prefix_general = 'pr_article_';
    var class_prefix_theme = 'pr_article_birdy';

    var general_classes = {
        'text_size': 'big,bigger,biggest,smallest,small,smaller,normal',
        'text_decoration': 'underline,normal',
        'text_style': 'b,i',
        'text_script': 'sup,sub',
        'float': 'left,right'
    };

    var theme_classes = {
        'text_color': 'red,gray,normal',
        'background_color': 'gray,normal'
    };

    var text_classes = ['text_size', 'text_decoration', 'text_style', 'text_script', 'text_color', 'background_color'];
    var layout_classes = ['float'];
    var wh_styles = {'width': '^[^d]*(px|em)$', 'height': '^[^d]*(px|em)$'};

    var allowed_tags_skeleton = [
        {
            tags: 'div,table,columns',
            classes: [].concat(text_classes, layout_classes)
        },
        {
            tags: 'div,table',
            styles: wh_styles
        },
        {
            tags: 'img',
            styles: wh_styles,
            classes: layout_classes
        },
        {
            tags: 'columns',
            attributes: {'number': '.*'}
        }
    ];

    var allowed_tags = {};
    $.each(allowed_tags_skeleton, function (del_ind, tags_and_properties) {

        var tags = tags_and_properties['tags'].split(',');

        var styles = tags_and_properties['styles'] ? tags_and_properties['styles'] : {};
        var attributes = tags_and_properties['attributes'] ? tags_and_properties['attributes'] : {};
        var classes = tags_and_properties['classes'] ? tags_and_properties['classes'] : {};


        $.each(tags, function (del_ind2, tag) {

            if (!allowed_tags[tag]) allowed_tags[tag] = {'classes': [], 'attributes': {}, 'styles': {}};

            $.each(styles, function (style_name, allowed_style_regexp) {
                if (allowed_tags[tag]['styles'][style_name]) {
                    console.error('error. regexp for style `' + style_name + '` for tag `' + tag + '` already defined as `' + allowed_tags[tag]['styles'][style_name] + '` ignored');
                }
                else {
                    allowed_tags[tag]['styles'][style_name] = allowed_style_regexp;
                }
            });

            $.each(attributes, function (attr_name, allowed_attr_regexp) {
                if (allowed_tags[tag]['attributes'][attr_name]) {
                    console.error('error. regexp for attribute `' + attr_name + '` for tag `' + tag + '` already defined as `' + allowed_tags[tag]['attributes'][attr_name] + '` ignored');
                }
                else {
                    allowed_tags[tag]['attributes'][attr_name] = allowed_attr_regexp;
                }
            });

            $.each(classes, function (del_ind3, classes_group_index) {
                if (theme_classes[classes_group_index]) {
                    class_sufixes = theme_classes[classes_group_index];
                }
                else if (general_classes[classes_group_index]) {
                    class_sufixes = general_classes[classes_group_index];
                }

                if (!class_sufixes) {
                    console.error('error. unknown class group index `' + classes_group_index + '` for tag `' + tag + '`. ignored');
                }
                else {
                    if (!allowed_tags[tag]['classes'][classes_group_index]) allowed_tags[tag]['classes'][classes_group_index] = [];
                    allowed_tags[tag]['classes'][classes_group_index] = [].concat(allowed_tags[tag]['classes'][classes_group_index],
                        _.map(class_sufixes.split(','), function (classsufix) {
                            return 'pr_article_' + classes_group_index + '_' + classsufix;
                        }));
                }
            });
        });
    });

    return allowed_tags;
}

function find_and_build_url_for_endpoint(dict, rules, host) {
    var found = false;
    var dict1 = {};

    $.each(rules, function (ind, rule) {
        var ret = rule;
        var prop = null;
        var dict1 = $.extend({}, dict);
        for (prop in dict1) {
            ret = ret.replace('<' + prop + '>', dict[prop]);
            delete dict1[prop];
        }
        if (!ret.match('<[^<]*>')) {
            found = ret;
            return false;
        }
    });

    if (found === false) {
        console.error('Can`t found flask endpoint for passed dictionary', dict, rules);
        return '';
    }
    else {
        if (_.size(dict1) > 0) {
            console.warn("Too many parameters passed in dictionary for endpoint rule", dict, rules);
        }
        return (host ? ('//' + host) : '') + found;
    }
}

var compile_regexps = function (format_properties) {
    //var rem = format_properties['remove_classes_on_apply'] ?
    //    RegExp('^' + format_properties['remove_classes_on_apply'] + '$', "i") : false;
    //console.log(format_properties);

    var rem = false;
    if (format_properties['remove_classes_on_apply']) {
        rem = {};
        $.each(format_properties['remove_classes_on_apply'], function (del, class_to_rem) {
            rem[class_to_rem] = RegExp('^' + class_to_rem + '$', "i")
        });
    }

    var add = false;
    if (format_properties['add_classes_on_apply']) {
        add = {};
        $.each(format_properties['add_classes_on_apply'], function (class_to_add, check_if_not_exust) {
            add[class_to_add] = RegExp('^' + check_if_not_exust + '$', "i")
        });
    }
    delete format_properties['add_classes_on_apply'];
    delete format_properties['remove_classes_on_apply'];
    //console.log({remove: rem, add: add});
    return {remove: rem, add: add};
};

var add_or_remove_classes = function (element, classes, remove, add) {

    console.log(element, classes, remove, add);

    classes.map(function (class_name) {
        if (add) {
            $.each(add, function (add_if_not_exist, check_if_exist) {
                if (check_if_exist && class_name.match(check_if_exist)) {
                    delete add[add_if_not_exist];
                }
            });
        }
    });

    $.each(add, function (add_if_not_exist, check_if_exist) {
        $(element).addClass(add_if_not_exist);
    });

    $.each(remove, function (del, remove_regexp) {
        classes.map(function (class_name) {
            if (class_name.match(remove_regexp))
                $(element).removeClass(class_name);
        });

    });
};

var extract_formats_items_from_group = function (formats_in_group) {
    var ret = [];
    $.each(formats_in_group, function (format_name, format) {
        ret.push(
            {title: format_name.replace(/.*_(\w+)$/, '$1'), format: format_name});
    });
    return ret;
}


var get_complex_menu = function (formats, name, subformats) {
    var ret = [];
    $.each(subformats, function (del, group_label) {
        ret.push({
            'title': group_label,
            items: extract_formats_items_from_group(formats[name + '_' + group_label])
        });
    });
    return ret;
}

var get_array_for_menu_build = function (formats) {
    var menu = {};
    menu['foreground'] = [{items: extract_formats_items_from_group(formats['foreground_color'])}];
    menu['background'] = [{items: extract_formats_items_from_group(formats['background_color'])}];
    menu['font'] = [{items: extract_formats_items_from_group(formats['font_family'])}];
    menu['border'] = get_complex_menu(formats, 'border', ['placement', 'type', 'width', 'color']);
    menu['margin'] = get_complex_menu(formats, 'margin', ['placement', 'size']);
    menu['padding'] = get_complex_menu(formats, 'padding', ['placement', 'size']);


    //menu['background_color'] = {
    //    'title': 'background',
    //    'items': extract_formats_items_from_group(formats['background_color'])
    //};
    //menu['font_family'] = {'title': 'font', 'items': extract_formats_items_from_group(formats['font_family'])};
    //
    //$.each(formats, function (format_group_name, formats_in_group) {
    //    var ret1 = {'title': format_group_name, 'items': []};
    //    $.each(formats_in_group, function (format_name, format) {
    //        ret1['items'].push(
    //            {title: format_name.replace(/.*_(\w+)$/, '$1'), format: format_name});
    //    });
    //    ret.push(ret1);
    //});
    return menu;
};


var convert_python_format_to_tinymce_format = function (python_format) {

    if (python_format['remove_classes_on_apply'] || python_format['add_classes_on_apply']) {

        var rem_add = compile_regexps(python_format);

        python_format['onformat'] = function (DOMUtils, element) {
            var classes = $(element).attr('class');
            add_or_remove_classes(element, classes ? classes.split(/\s+/) : [], rem_add['remove'], rem_add['add']);
        }
    }
    return python_format;
};


// #TODO: OZ by OZ: remove this function. urls should be formed at ss
var noImageForImageName = function (image_name) {
    if (image_name === 'logo_file_id') {
        return static_address('images/company_no_logo.png');
    }
    else {
        return static_address('images/no_image.png');
    }
}

window.lastUserActivity = now();
window.onUserActivity = {};
$('body').bind('mousedown keydown', function (event) {
    window.lastUserActivity = now();
    $.each(window.onUserActivity, function (ind, func) {
        func();
    })
});

