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


angular.module('profireaderdirectives', ['ui.bootstrap', 'ui.bootstrap.tooltip'])
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
    .directive('highlighter', ['$timeout', function ($timeout) {
        return {
            restrict: 'A',
            link: function (scope, element, attrs) {
                scope.$watch(attrs.highlighter, function (nv, ov) {
                    if (nv !== ov) {
                        // apply class
                        element.addClass('highlight');
                        // auto remove after some delay
                        $timeout(function () {
                            element.removeClass('highlight');
                        }, 500);
                    }
                });
            }
        };
    }]).directive('ngValidateUrl', ['$http', '$compile', function ($http, $compile) {

        return {
            restrict: 'A'
            , link: function (scope, iElement, iAttrs, ctrl) {
                scope.areAllEmpty = function () {
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

                scope.checking = {};
                scope.checked = {};
                scope.data = {};

                scope.errors = {};
                scope.warnings = {};
                scope.dirty = true;

                $.each($('[name]', $(iElement)), function (ind, el) {
                    $newel = $(el).clone()
                    $newel.attr('ng-model', 'data.' + $newel.attr('name'));
                    $(el).replaceWith($compile($newel)(scope))
                });

                scope.getSignificantClass = function (index, one, onw, onn) {

                    if (scope.errors && !scope.areAllEmpty(scope.errors[index])) {
                        return one;
                    }
                    if (scope.warnings && !scope.areAllEmpty(scope.warnings[index])) {
                        return onw;
                    }
                    if (scope.notices && !scope.areAllEmpty(scope.notices[index])) {
                        return onn;
                    }
                    return '';
                };

                scope.getSignificantMessage = function (index) {

                    if (scope.errors && !scope.areAllEmpty(scope.errors[index])) {
                        return scope.errors[index][0];
                    }
                    if (scope.warnings && !scope.areAllEmpty(scope.warnings[index])) {
                        return scope.warnings[index][0];
                    }
                    if (scope.notices && !scope.areAllEmpty(scope.notices[index])) {
                        return scope.notices[index][0]
                    }
                    return '';
                };

                scope.url = iAttrs['ngValidateUrl'];


                scope.refresh = function () {
                    console.log('refresh');
                    scope.changed = getObjectsDifference(scope.checked, scope['data']);
                    scope.check();
                };

                scope.check = _.debounce(function (d) {
                    if (scope.areAllEmpty(scope.checking)) {
                        console.log('scope.changed', scope.changed);
                        scope.changed = getObjectsDifference(scope.checked, scope['data']);
                        if (!scope.areAllEmpty(scope.changed)) {
                            scope.checking = scope['data'];
                            $http.post(scope.url, scope.checking)
                                .then(function (fromserver) {
                                    var resp = fromserver['data'];
                                    if (scope.areAllEmpty(getObjectsDifference(scope.checking, scope['data']))) {
                                        scope.errors = $.extend(true, {}, resp['errors']);
                                        scope.warnings = $.extend(true, {}, resp['warnings']);
                                        scope.checked = $.extend(true, {}, scope.checking);
                                        scope.changed = {};
                                        scope.checking = {};
                                    }
                                    else {
                                        scope.checking = {};
                                        scope.refresh();
                                    }
                                }, function () {
                                    scope.checking = {};
                                    scope.refresh();
                                });
                        }
                    }
                    else {
                        scope.refresh();
                    }
                }, 500);

                scope.$watch('data', scope.refresh, true);
                scope.refresh();
                //            scope.getTemp(iAttrs.ngCity);
            }
        };
    }]);