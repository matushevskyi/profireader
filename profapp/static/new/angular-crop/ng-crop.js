/**
 /**
 * Created by oles on 07.04.16.
 */

(function (angular) {

    'use strict';
    if (!angular) {
        throw 'No angular found';
    }

    var ri = function (f) {
        return Math.round(f * 100000) / 100000;
    };

    var rc = function (f) {
        return Math.round(f * 100000) / 100000;
    };

    var px = function (n) {
        return ('' + n + 'px');
    };

    var inRange = function (v, min, max) {
        return Math.min(Math.max(min, v), max);
    };

    var createCompass = function (f) {
        f = f ? f : 0.5;
        return {w: f, e: f, s: f, n: f};
    };

    var compileTemplate = function ($scope, $compile, element) {
        element.html('<div class="ng-crop-container">' +
            '<div class="ng-crop-loading"></div>' +
            '<div class="ng-crop-canvas">' +
            // '<canvas class="ng-crop-canvas"></canvas>' +
            '<div ng-crop-action="set" class="ng-crop-set"></div>' +
            '<div ng-crop-action="move" class="ng-crop-move"></div>' +
            '<div ng-crop-action="nw" class="ng-crop-resize ng-crop-rect-n ng-crop-rect-w"></div>' +
            '<div ng-crop-action="n" class="ng-crop-resize ng-crop-rect-n"></div>' +
            '<div ng-crop-action="ne" class="ng-crop-resize ng-crop-rect-n ng-crop-rect-e"></div>' +
            '<div ng-crop-action="e" class="ng-crop-resize ng-crop-rect-e"></div>' +
            '<div ng-crop-action="se" class="ng-crop-resize ng-crop-rect-s ng-crop-rect-e"></div>' +
            '<div ng-crop-action="s" class="ng-crop-resize ng-crop-rect-s"></div>' +
            '<div ng-crop-action="sw" class="ng-crop-resize ng-crop-rect-s ng-crop-rect-w"></div>' +
            '<div ng-crop-action="w" class="ng-crop-resize ng-crop-rect-w"></div>' +
            '</div></div>');

        $compile(element.contents())($scope);
    };

    var collectElements = function ($scope, element) {

        $scope.$e = function (selector) {
            return $(selector, element);
        };

        $scope.$element_actions = $scope.$e('*[ng-crop-action]');

        $scope.$element_corners = $scope.$e('.ng-crop-resize');
        $scope.$element_corners_w = $scope.$e('.ng-crop-rect-w');
        $scope.$element_corners_e = $scope.$e('.ng-crop-rect-e');
        $scope.$element_corners_n = $scope.$e('.ng-crop-rect-n');
        $scope.$element_corners_s = $scope.$e('.ng-crop-rect-s');

        $scope.$element_action_move = $scope.$e('.ng-crop-move');
        $scope.$element_action_set = $scope.$e('.ng-crop-set');

        // $scope.$img = $scope.$e('img');
        $scope.$canvas = $scope.$e('.ng-crop-canvas');
        $scope.$container = $scope.$e('.ng-crop-container');
        $scope.$loading = $scope.$e('.ng-crop-loading');
    };

    var Logic = function (img, opts, $container) {

        this.canvas2imgX = function (cx, state) {
            return ri(cx / state.zoom + state.origin[0]);
        };

        this.canvas2imgY = function (cy, state) {
            return ri(cy / state.zoom + state.origin[1]);
        };

        this.canvas2imgW = function (w, state) {
            return ri(w / state.zoom);
        };

        this.canvas2imgH = function (h, state) {
            return ri(h / state.zoom);
        };

        this.canvas2imgRect = function (canvasrect, state) {
            return canvasrect ? [
                this.canvas2imgX(canvasrect[0], state), this.canvas2imgY(canvasrect[1], state),
                this.canvas2imgX(canvasrect[2], state), this.canvas2imgY(canvasrect[3], state)] : null;
        };

        this.canvas2imgPoint = function (canvaspoint, state) {
            return canvaspoint ?
                [this.canvas2imgX(canvaspoint[0], state), this.canvas2imgY(canvaspoint[1], state)] : null;
        };

        this.img2canvasX = function (ix, state) {
            return rc((ix - state.origin[0]) * state.zoom);
        };

        this.img2canvasY = function (iy, state) {
            return rc((iy - state.origin[1]) * state.zoom);
        };

        this.img2canvasW = function (w, state) {
            return rc(w * state.zoom);
        };

        this.img2canvasH = function (h, state) {
            return rc(h * state.zoom);
        };

        this.img2canvasPoint = function (imgpoint, state) {
            return imgpoint ?
                [this.img2canvasX(imgpoint[0], state), this.img2canvasY(imgpoint[1], state)] : null;
        };

        this.img2canvasRect = function (imgrect, state) {
            return imgrect ? [
                this.img2canvasX(imgrect[0], state), this.img2canvasY(imgrect[1], state),
                this.img2canvasX(imgrect[2], state), this.img2canvasY(imgrect[3], state)] : null;
        };

        this.lessThenWithDeviation = function (what, inrespectto, deviation) {
            return (what < inrespectto || this.relativeDeviationIn(what, inrespectto, deviation)) ? true : false;
        }

        this.relativeDeviationIn = function (v, in_respect_to, maxDeviation) {
            var max = maxDeviation ? maxDeviation : 0.000001;
            return Math.abs(v - in_respect_to) / in_respect_to <= max;
        };


        this.scaleRect = function (rect, zoom_ratio, compass) {
            var oldcx = (rect[2] + rect[0]) / 2.;
            var oldcy = (rect[3] + rect[1]) / 2.;
            var oldw = (rect[2] - rect[0]) / 1.;
            var oldh = (rect[3] - rect[1]) / 1.;
            var nw = oldw * zoom_ratio;
            var nh = oldh * zoom_ratio;
            var ret = [
                oldcx - oldw / 2. - (nw - oldw) / 2. * compass.w,
                oldcy - oldh / 2. - (nh - oldh) / 2. * compass.n,
                oldcx + oldw / 2. + (nw - oldw) / 2. * compass.e,
                oldcy + oldh / 2. + (nh - oldh) / 2. * compass.s];
            // console.log('scaleRect old center', oldcx, oldcy);
            // console.log('scaleRect old size', (rect[2] - rect[0]), (rect[3] - rect[1]));
            // console.log('scaleRect old rect', rect);
            // console.log('scaleRect zoom ratio, compass', zoom_ratio, compass);
            // console.log('scaleRect new center', (ret[2] + ret[0]) / 2, (ret[3] + ret[1]) / 2);
            // console.log('scaleRect new size', (ret[2] - ret[0]), (ret[3] - ret[1]));
            // console.log('scaleRect onew rect', ret);
            return ret;

        };

        this.fitZoomAndOriginByCoordinates = function (coords, zoom, origin) {
            var ret = {}
            // TODO: calculate (from coordinates changes) and pass compass here
            // coordinates is main. use it first
            coords = this.fitByImageConstrains(coords);
            ret.coordinates = coords;

            // than zoom
            var max_zoom = Math.min(this.ctr.canvas_size[0] / (coords[2] - coords[0]),
                this.ctr.canvas_size[1] / (coords[3] - coords[1]));
            ret.zoom = inRange(zoom, this.ctr.min_zoom, max_zoom);


            // canvas and image sizes (in image dimension)
            var wc = this.ctr.canvas_size[0] / ret.zoom;
            var hc = this.ctr.canvas_size[1] / ret.zoom;
            var wi = this.ctr.image_size[0];
            var hi = this.ctr.image_size[1];


            // than origin
            // use compas here (yes that compas that used to be calculated a few lines earler)

            if (origin) {
                ret.origin = origin;
                ret.origin[0] = inRange(origin[0], coords[2] - wc, coords[0]);
                ret.origin[1] = inRange(origin[1], coords[3] - hc, coords[1]);
            }
            else {
                ret.origin = [(wc - (coords[2] - coords[0])) / 2., (hc - (coords[3] - coords[1])) / 2.]
                ret.origin[0] = inRange(ret.origin[0], coords[2] - wc, coords[0]);
                ret.origin[1] = inRange(ret.origin[1], coords[3] - hc, coords[1]);
            }
            ret.origin[0] = inRange(ret.origin[0], 0, wi - wc);
            ret.origin[1] = inRange(ret.origin[1], 0, hi - hc);


            return ret;
        };

        this.fitCoordinatesAndOriginByZoom = function (coords, zoom, origin, center_point) {
            var ret = {};
            // maybe we should calculate and use compass in this function

            // first zoom. it's main
            ret.zoom = inRange(zoom, this.ctr.min_zoom, this.ctr.max_zoom);


            // canvas and image sizes (in image dimension)
            var wc = this.ctr.canvas_size[0] / ret.zoom;
            var hc = this.ctr.canvas_size[1] / ret.zoom;
            var wi = this.ctr.image_size[0];
            var hi = this.ctr.image_size[1];

            if (!coords) {
                if (!origin) {
                    origin = [(wi - wc) / 2., (hi - hc) / 2.];
                }
                else {
                    origin = [inRange(origin[0], 0, wi - wc), inRange(origin[1], 0, hi - hc)];
                }
                coords = [ri(origin[0] + wc / 10.), ri(origin[1] + hc / 10.), ri(origin[0] + wc * 9 / 10.), ri(origin[1] + hc * 9 / 10.)];
            }
            else {
                // use compass

                var w = coords[2] - coords[0];
                var h = coords[3] - coords[1];
                var cx = (coords[2] + coords[0]) / 2.;
                var cy = (coords[3] + coords[1]) / 2.;
                if (!center_point) center_point = [cx, cy];
                if (w > wc) {
                    coords[0] = center_point[0] - wc / 2;
                    coords[2] = center_point[0] + wc / 2;
                }
                if (h > hc) {
                    coords[1] = center_point[1] - hc / 2;
                    coords[3] = center_point[1] + hc / 2;
                }
                origin = [center_point[0] - (wc - (coords[2] - coords[0])), center_point[1]];
            }

            ret.origin = [];
            ret.origin[0] = inRange(origin[0], 0, wi - wc);
            ret.origin[1] = inRange(origin[0], 0, hi - hc);

            ret.coordinates = this.fitByConstrains(coords, ret);

            console.log(ret);

            return ret;


        }

        this.fitByImageConstrains = function (imgrect, compass) {

            compass = compass ? compass : createCompass(0.5);


            // scale canvas rect by image constrains (min/max size, aspect) and canvas size
            var ret = [imgrect[0], imgrect[1], imgrect[2], imgrect[3]];

            var max_w = this.ctr.max_width;
            var max_h = this.ctr.max_height;
            var min_w = this.ctr.min_width;
            var min_h = this.ctr.min_height;

            var asp = (imgrect[2] - imgrect[0]) / (imgrect[3] - imgrect[1]);

            if (asp > this.ctr.max_aspect) {
                // console.log('aspect >');

                max_w = (imgrect[3] - imgrect[1]) * this.ctr.max_aspect;
                // TODO: OZ by OZ: zhis is ok? maybe in next line should be `max_w > this.ctr.max_width`,
                // and then `else if `(max_w < this.ctr.min_width)` ???
                if (max_w < this.ctr.min_width) {
                    max_w = this.ctr.min_width;
                }
                else if (max_w > this.ctr.max_width) {
                    throw new RangeError;
                }

            }
            else if (asp < this.ctr.min_aspect) {
                // console.log('aspect <');

                max_h = (imgrect[2] - imgrect[0]) / this.ctr.min_aspect;
                if (max_h < this.ctr.min_height) {
                    max_h = this.ctr.min_height;
                }
                else if (max_h > this.ctr.max_height) {
                    throw new RangeError;
                }
            }

            if (imgrect[2] - imgrect[0] > max_w) {
                // console.log('w >', imgrect[2] - imgrect[0], max_w);
                ret[0] = imgrect[0] + compass.w * (imgrect[2] - imgrect[0] - max_w);
                ret[2] = imgrect[2] + compass.e * (imgrect[0] - imgrect[2] + max_w);
            }
            else if (imgrect[2] - imgrect[0] < min_w) {
                // console.log('w <', imgrect[2] - imgrect[0], min_w);
                ret[0] = imgrect[0] + compass.w * (imgrect[2] - imgrect[0] - min_w);
                ret[2] = imgrect[2] + compass.e * (imgrect[0] - imgrect[2] + min_w);
            }

            if (imgrect[3] - imgrect[1] > max_h) {
                // console.log('h >', imgrect[3] - imgrect[1], max_h);
                ret[1] = imgrect[1] + compass.n * (imgrect[3] - imgrect[1] - max_h);
                ret[3] = imgrect[3] + compass.s * (imgrect[1] - imgrect[3] + max_h);
            }
            else if (imgrect[3] - imgrect[1] < min_h) {
                // console.log('h <', imgrect[3] - imgrect[1], min_h);
                ret[1] = imgrect[1] + compass.n * (imgrect[3] - imgrect[1] - min_h);
                ret[3] = imgrect[3] + compass.s * (imgrect[1] - imgrect[3] + min_h);
            }
            return ret;
        };

        this.fitByConstrains = function (imgrect, state, compass) {

            // console.log('passed image rect', imgrect);

            var ret = this.img2canvasRect(this.fitByImageConstrains(imgrect, compass), state);

            // console.log('constrains by img', ret);

            // image scaled by max min size and aspect ratio go out of cancas
            // let' try move it
            var ret_copy = ret.slice();
            if (ret[0] < 0) {
                // console.log('moving right', ret[0]);
                ret[2] = ret[2] - ret[0];
                ret[0] = 0;
            }
            if (ret[1] < 0) {
                // console.log('moving right', ret[1]);
                ret[3] = ret[3] - ret[1];
                ret[1] = 0;
            }
            if (ret[3] > this.ctr.canvas_size[1]) {
                // console.log('moving right', ret[3], this.ctr.canvas_size[1]);
                ret[1] = ret[1] - (ret[3] - this.ctr.canvas_size[1]);
                ret[3] = this.ctr.canvas_size[1];
            }
            if (ret[2] > this.ctr.canvas_size[0]) {
                // console.log('moving right', ret[2], this.ctr.canvas_size[0]);
                ret[0] = ret[0] - (ret[2] - this.ctr.canvas_size[0]);
                ret[2] = this.ctr.canvas_size[0];
            }

            // ok, still out of canvas. let's try scale it
            if (ret[0] < 0 || ret[1] < 0) {
                // console.log('moving right', ret, this.ctr.canvas_size);
                if (ret[2] - ret[0] > this.ctr.canvas_size[0]) {
                    ret[0] = 0;
                    ret[2] = this.ctr.canvas_size[0];
                }
                if (ret[3] - ret[1] > this.ctr.canvas_size[1]) {
                    ret[1] = 0;
                    ret[3] = this.ctr.canvas_size[1];
                }

                ret = this.img2canvasRect(this.fitByImageConstrains(this.canvas2imgRect(ret, state), compass), state);

                if (!this.lessThenWithDeviation(ret[2] - ret[0], this.ctr.canvas_size[0]) || !this.lessThenWithDeviation(ret[3] - ret[1], this.ctr.canvas_size[1])) {

                    // if (ret[2] - ret[0] > this.ctr.canvas_size[0] || ret[3] - ret[1] > this.ctr.canvas_size[1]) {
                    console.log('calculated canvas rect', ret);
                    console.log('current constrains', this.ctr);
                    throw "current canvas can't satisfy all constrains"
                }
            }

            return this.canvas2imgRect(ret, state);
        }


        this.addDXDY = function (canvasrect, mousedxdy) {

            var ret = [canvasrect[0], canvasrect[1], canvasrect[2], canvasrect[3]];
            mousedxdy = mousedxdy ? mousedxdy : [0, 0];

            if (mousedxdy.length === 2) mousedxdy.push(mousedxdy[0], mousedxdy[1]);

            for (var i = 0; i < 4; i++) ret[i] += mousedxdy[i];
            return ret;
        };

        this.calculateConstrains = function () {
            var o = opts;

            if (!this.img) {
                this.ctr = null;
                return false;
            }

            if (this.img.naturalWidth < o['min_width']) {
                throw new RangeError("Image to narrow for minimal width");
            }
            if (this.img.naturalHeight < o['min_height']) {
                throw new RangeError("Image to narrow for minimal height");
            }


            // TODO: check mage size and min/max can be meet
            // var aspect = img.naturalWidth / img.naturalHeight;
            // if (aspect)
            //
            //


            var ctr = {};
            ctr.image_size = [this.img.naturalWidth, this.img.naturalHeight];
            ctr.max_width = Math.min(ctr.image_size[0], o['max_width']);
            ctr.max_height = Math.min(ctr.image_size[1], o['max_height']);
            ctr.min_width = Math.max(1, o['min_width']);
            ctr.min_height = Math.max(1, o['min_height']);
            ctr.max_aspect = Math.min(Infinity, o['max_aspect']);
            ctr.min_aspect = Math.max(0, o['min_aspect']);
            ctr.max_zoom = o.max_zoom;


            var image_wider_than_container = ctr.image_size[0] * $container.height() / ctr.image_size[1] / $container.width();
            var img_based_min_zoom = 0;
            ctr.canvas_size = [0, 0];
            if (image_wider_than_container > 1) {
                img_based_min_zoom = $container.width() / ctr.image_size[0];
                ctr.canvas_size = [$container.width(), $container.height() / image_wider_than_container];
            }
            else {
                img_based_min_zoom = $container.height() / ctr.image_size[1];
                ctr.canvas_size = [$container.width() * image_wider_than_container, $container.height()];
            }

            // shrink canvas if min zoom overfit container
            if (img_based_min_zoom > ctr.max_zoom) {
                ctr.canvas_size = [ctr.canvas_size[0] / (img_based_min_zoom / ctr.max_zoom), ctr.canvas_size[1] / (img_based_min_zoom / ctr.max_zoom)];
                img_based_min_zoom = ctr.max_zoom;
            }

            ctr.min_zoom = Math.max(o.min_zoom, img_based_min_zoom);

            return ctr;

        };

        this.img = img;

        this.ctr = this.calculateConstrains();

    };

    var cropLinkFunc = function ($scope, $q, $timeout, element, attrs, model) {


        $scope.loading = true;
        $scope.canvas_for_current_zoom = null;
        // $scope.url = null;
        $scope.options = null;
        $scope.REDRAW_NEW_RECT = 'REDRAW_NEW_RECT';
        $scope.REDRAW_NEW_ZOOM = 'REDRAW_NEW_ZOOM';
        $scope.REDRAW_NEW_IMAGE = 'REDRAW_NEW_IMAGE';
        $scope.state = null;

        $scope.setState = function (state) {
            $scope.state = state;
        };


        $scope.getSavedState = function () {
            return $scope.state;
        };

        $scope.setState({
            crop: null,

            coordinates: null,
            origin: null,
            zoom: null,

            disabled: true,

            loading: true,
            // img: null,
            logic: null
        });


        $scope.$watch('ngCropOptions', function (newv, oldv) {

            // console.log(newv);

            var opts = {};

            var isnum = function (newval, key, already_assigned_opts) {
                return (typeof newval === 'number') ? true : (key + " should be number");
            };

            var isnumandgt1 = [1, isnum, function (newval, key, already_assigned_opts) {
                return (newval >= 1) ? true : (key + " should be > 1");
            }];
            var isnumandgt0 = [0, isnum, function (newval, key, already_assigned_opts) {
                return (newval >= 0) ? true : (key + " should be > 0");
            }];
            var isnumandi = [Infinity, isnum];


            angular.forEach({
                'min_zoom': isnumandgt0,
                'max_zoom': isnumandgt1.concat([function (newval, key, already_assigned_opts) {
                    return (newval >= already_assigned_opts['min_zoom']) ? true : " max_zoom is < min_zoom";
                }]),

                'min_width': isnumandgt1,
                'max_width': isnumandi.concat([function (newval, key, already_assigned_opts) {
                    return (newval >= already_assigned_opts['min_width']) ? true : " max_width is < min_width";
                }]),
                'min_height': isnumandgt1,
                'max_height': isnumandi.concat([function (newval, key, already_assigned_opts) {
                    return (newval >= already_assigned_opts['min_height']) ? true : " max_height is < min_height";
                }]),
                'min_aspect': isnumandgt0,
                'max_aspect': isnumandi.concat([function (newval, key, already_assigned_opts) {
                    return (newval >= already_assigned_opts['min_aspect']) ? true : " max_aspect is < min_aspect";
                }]),
            }, function (def_and_cond, key) {
                var default_value = def_and_cond[0];
                var some_condition_broken = !newv || !newv.hasOwnProperty || !newv.hasOwnProperty(key);
                if (!some_condition_broken) {
                    var newvalue = newv[key];
                    for (var i = 1; i < def_and_cond.length; i++) {
                        var check_condition = def_and_cond[i](newvalue, key, opts);
                        if (check_condition !== true) {
                            some_condition_broken = true;
                            console.error(check_condition);
                        }
                    }
                }
                opts[key] = some_condition_broken ? default_value : newvalue;
            });

            $scope.options = opts;

        });


        $scope.setCoordinates = function (FixedPoint) {
            console.log('setCoordinates');
            if (!$scope.logic || !$scope.logic.img) return;
            // this function is called when coordinates was changed.
            // in this case zoom and origin (whatever old or new values) are preserved only if
            // they can satisfy new coordinates
            var ctr = $scope.logic.ctr;
            if (!$scope.ngCropCoordinates) { // we haven't coordinates. so we calculate coordinates based on zoom
                $scope.ngCropZoom = inRange($scope.ngCropZoom, ctr.min_zoom, ctr.max_zoom);
                var center = [ctr.image_size[0] / 2., ctr.image_size[1] / 2.];
                var canvas_size = [ctr.canvas_size[0] / $scope.ngCropZoom, ctr.canvas_size[1] / $scope.ngCropZoom];
                $scope.ngCropCoordinates = [center[0] - 4 * canvas_size[0] / 10, center[1] - 4 * canvas_size[1] / 10, center[0] + 4 * canvas_size[0] / 10, center[1] + 4 * canvas_size[1] / 10];
                // default coordinates can be out of constrains. check it
                $scope.ngCropCoordinates = $scope.logic.fitByImageConstrains($scope.ngCropCoordinates);
            }
            else { // we have coordinates and they was changed. first check if this coordinates fit into image and
                // constrains
                $scope.ngCropCoordinates = $scope.logic.fitByImageConstrains($scope.ngCropCoordinates);
                // now check zoom. can we preserve it?
                // zoom must be sufficient small to fit new requested rect
                var max_zoom = Math.min(ctr.canvas_size[0] / ($scope.ngCropCoordinates[2] - $scope.ngCropCoordinates[0]), ctr.canvas_size[1] / ($scope.ngCropCoordinates[3] - $scope.ngCropCoordinates[1]));
                $scope.ngCropZoom = inRange($scope.ngCropZoom, ctr.min_zoom, max_zoom);
            }

            var canvas_size = [ctr.canvas_size[0] / $scope.ngCropZoom, ctr.canvas_size[1] / $scope.ngCropZoom];
            var crop_center = [($scope.ngCropCoordinates[0] + $scope.ngCropCoordinates[2]) / 2., ($scope.ngCropCoordinates[1] + $scope.ngCropCoordinates[3]) / 2.];
            if (!$scope.ngCropOrigin) { // we have now coordinates and zoom. can we preserve image center?
                $scope.ngCropOrigin = [crop_center[0] - canvas_size[0] / 2, crop_center[1] - canvas_size[1] / 2];
            }
            console.log($scope.ngCropOrigin);
            $scope.ngCropOrigin = [inRange($scope.ngCropOrigin[0], $scope.ngCropCoordinates[2] - canvas_size[0], $scope.ngCropCoordinates[0]),
                inRange($scope.ngCropOrigin[1], $scope.ngCropCoordinates[3] - canvas_size[1], $scope.ngCropCoordinates[1])];
            $scope.ngCropOrigin = [inRange($scope.ngCropOrigin[0], 0, ctr.image_size[0] - canvas_size[0]), inRange($scope.ngCropOrigin[1], 0, ctr.image_size[1] - canvas_size[1])];
        };

        $scope.setZoom = function (FixedPoint) {
            console.log('setZoom', FixedPoint);
            if (!$scope.logic || !$scope.logic.img) return;

            // this function is called when zoom was changed and coordianates do not.
            // in this case old coordinates and old (or new) origin are preserved only if they can satisfy new zoom
            // additional FixedPoint is passed if we want to size canvas relative to this point
            var ctr = $scope.logic.ctr;

            $scope.ngCropZoom = inRange($scope.ngCropZoom, ctr.min_zoom, ctr.max_zoom);
            var canvas_size = [ctr.canvas_size[0] / $scope.ngCropZoom, ctr.canvas_size[1] / $scope.ngCropZoom];
            if (!$scope.ngCropCoordinates) { // we haven't coordinates. so we calculate coordinates based on zoom
                var center = FixedPoint ? [FixedPoint[0], FixedPoint[1]] : [ctr.image_size[0] / 2., ctr.image_size[1] / 2.]
                $scope.ngCropCoordinates = [center[0] - 9 * canvas_size[0] / 10, center[1] - 9 * canvas_size[1] / 10, center[0] + 9 * canvas_size[0] / 10, center[1] + 9 * canvas_size[1] / 10];
                // default coordinates can be out of constrains. check it
                $scope.ngCropCoordinates = $scope.logic.fitByImageConstrains($scope.ngCropCoordinates);
            }
            else {
                $scope.ngCropCoordinates = $scope.logic.fitByImageConstrains($scope.ngCropCoordinates);
                // we have coordinates. can we preserve it?
                // if no fixedPoint passed - we try to zoom in out relative to coordinates center
                // debugger;
                FixedPoint = FixedPoint ? FixedPoint : [($scope.ngCropCoordinates[0] + $scope.ngCropCoordinates[2]) / 2.,
                    ($scope.ngCropCoordinates[1] + $scope.ngCropCoordinates[3]) / 2.];
                // we have fixed point and old canvas coordinates, try to calculate compass based on this parameters
                var compass = createCompass(0.5);
                if ($scope.state.origin && $scope.state.zoom) { // of course if there WAS old canvas coordinates
                    var old_canvas_coordinates = [$scope.state.origin[0], $scope.state.origin[1], $scope.state.origin[0] + ctr.canvas_size[0] / $scope.state.zoom, $scope.state.origin[1] + ctr.canvas_size[1] / $scope.state.zoom];
                    compass = {
                        w: (FixedPoint[0] - old_canvas_coordinates[0]) / (old_canvas_coordinates[2] - old_canvas_coordinates[0]),
                        n: (FixedPoint[1] - old_canvas_coordinates[1]) / (old_canvas_coordinates[3] - old_canvas_coordinates[1])
                    };
                    compass.e = 1 - compass.w;
                    compass.s = 1 - compass.n;
                }
                console.log(FixedPoint, compass);
                // we have compass calculate new canvas coordinates, actually we need only top left corner (origin)

                var new_canvas_coordinates = [
                    FixedPoint[0] - canvas_size[0] * compass['w'], FixedPoint[1] - canvas_size[1] * compass['n'],
                    FixedPoint[0] + canvas_size[0] * compass['e'], FixedPoint[1] + canvas_size[1] * compass['s']];
                // console.log(compass, FixedPoint, canvas_size, new_canvas_coordinates);
                // ok. new canvas fit in image? we can check only one corner if it's fit another SHOULD fit by
                // zoom/coordinates constrains
                new_canvas_coordinates[0] = inRange(new_canvas_coordinates[0], 0, ctr.image_size[0] - (new_canvas_coordinates[2] - new_canvas_coordinates[0]));
                new_canvas_coordinates[1] = inRange(new_canvas_coordinates[1], 0, ctr.image_size[1] - (new_canvas_coordinates[3] - new_canvas_coordinates[1]));
                $scope.ngCropOrigin = new_canvas_coordinates;
                // console.log($scope.ngCropOrigin);
                // we have new origin and now coordinates can be out of canvas
                $scope.ngCropCoordinates = $scope.logic.fitByConstrains($scope.ngCropCoordinates, {
                    zoom: $scope.ngCropZoom,
                    origin: $scope.ngCropOrigin
                }, compass);
            }
        };

        $scope.setOrigin = function () {
            if (!$scope.logic || !$scope.logic.img) return;
            // TODO
            // in future we have to replace `origin` by `center` in croper and change
            // here zoom and coordinates (if we cant preserve it), also maybe `origin`=>`center` replace somehow
            // affect `FixedPoint` in $scope.setZoom function
        };

        $scope.coordinatesWasChanged = function (o, n) {
            return ((!o && n) || (o && !n) || (o && n && ((o[0] !== n[0]) || (o[1] !== n[1]) || (o[2] !== n[2]) || (o[3] !== n[3])))) ? true : false;
        };

        $scope.originWasChanged = function (o, n) {
            return ((!o && n) || (o && !n) || (o && n && ((o[0] !== n[0]) || (o[1] !== n[1])))) ? true : false;
        };

        $scope.zoomWasChanged = function (o, n) {
            return ((!o && n) || (o && !n) || (o && n && (o !== n))) ? true : false;
        };

        $scope.$watchCollection(function () {


            var getCollection = function () {
                var ret = {
                    img: ($scope.logic && $scope.logic.img) ? $scope.logic.img : null, // loaded image object
                    loading: $scope.loading, // image is loading or not
                    zoom: $scope.state.zoom ? $scope.state.zoom : null,
                    coordinates: $scope.state.coordinates ? $scope.state.coordinates.join(',') : null,
                    origin: $scope.state.origin ? $scope.state.origin.join(',') : null
                };
                return ret;
            };


            var image_changed = (!$scope.loading && (($scope.state.crop && !$scope.ngCrop) || (!$scope.state.crop && $scope.ngCrop) || ($scope.state.crop !== $scope.ngCrop)));
            if (!image_changed && $scope.loading && $scope.ngCrop !== $scope.loading_image_src) {
                image_changed = true;
            }

            if (image_changed) {

                console.log('image changed');

                if ($scope.loading_image) {
                    delete $scope.loading_image;
                    $scope.loading_image = null;
                    $scope.loading_image_src = null;
                }

                var storeState = function () {
                    $scope._stored = [$scope.state, $scope.logic, $scope.loading];
                };

                var reStoreState = function () {
                    if (!$scope._stored) return;
                    $scope.state = $scope._stored[0];
                    $scope.logic = $scope._stored[1];
                    $scope.loading = $scope._stored[2];
                    $scope.ngCrop = $scope.state.crop;
                    $scope.ngCropOrigin = $scope.state.origin;
                    $scope.ngCropDisabled = $scope.state.disabled;
                    $scope.ngCropCoordinates = $scope.state.coordinates;
                    $scope.ngCropZoom = $scope.state.zoom;
                };

                var err = function (e) {
                    reStoreState();
                    $scope.onError(typeof e === 'string' ? e : 'image loading error');
                    $timeout(function () {
                    })
                };


                if (!$scope.ngCrop) {
                    console.log('no image');
                    $scope.loading = false;
                    if ($scope.loading_image) delete $scope.loading_image;
                    $scope.loading_image = null;
                    $scope.loading_image_src = null;
                    $scope.ngCrop = null;
                    $scope.onLoad(null);
                }
                else {
                    storeState();
                    $scope.loading = true;
                    if ($scope.loading_image) delete $scope.loading_image;
                    $scope.loading_image = new Image()
                    $scope.loading_image.crossOrigin = "anonymous";
                    $scope.loading_image.onerror = err;
                    $scope.loading_image_src = $scope.ngCrop;
                    $scope.loading_image.onload = function () {
                        console.log('image loaded');
                        try {
                            var newl = new Logic($scope.loading_image, $scope.options, $scope.$container);
                            $scope.logic = newl;
                            $scope.state.loading = false;
                            $scope.state.crop = $scope.loading_image_src;
                            $scope.loading_image = null;
                            $scope.loading = false;
                            $scope.loading_image_src = null;
                            $scope.onLoad(newl);
                            $timeout(function () {
                            });
                        }
                        catch (e) {
                            err(e);
                        }
                    };

                    $scope.loading_image.src = $scope.ngCrop;

                }
                return getCollection();
            }
            else if ($scope.loading) {
                console.log('image still loading. we can`t apply changes now because constrains and' +
                    ' logic are unknown yet');
                return getCollection();
            }
            else {
                // console.log('something changed. not image');
                var coordinatesWasChanged = $scope.coordinatesWasChanged($scope.state.coordinates, $scope.ngCropCoordinates);
                var zoomWasChanged = $scope.zoomWasChanged($scope.state.zoom, $scope.ngCropZoom);
                var originWasChanged = $scope.originWasChanged($scope.state.origin, $scope.ngCropOrigin);

                if (coordinatesWasChanged) {
                    $scope.setCoordinates();
                }
                else if (zoomWasChanged) {
                    $scope.setZoom();
                }
                else if (originWasChanged) { // TODO
                    $scope.setOrigin();
                }
                else if (!$scope.ngCropCoordinates || !$scope.ngCropZoom || !$scope.ngCropOrigin) { // TODO
                    $scope.setCoordinates();
                }

                $scope.state.coordinates = $scope.ngCropCoordinates;
                $scope.state.origin = $scope.ngCropOrigin;
                $scope.state.zoom = $scope.ngCropZoom;
                $scope.state.disabled = $scope.ngCropDisabled;

                return getCollection();

            }


            // console.log('watch func', ret);
            // return encodeanswer(ret);
        }, function (newv, oldv) {
            var what_to_redraw = null;
            if (newv.coordinates !== oldv.coordinates) {
                what_to_redraw = $scope.REDRAW_NEW_RECT;
            }
            if (newv.zoom !== oldv.zoom) {
                what_to_redraw = $scope.REDRAW_NEW_ZOOM;
            }
            if (newv.img !== oldv.img) {
                what_to_redraw = $scope.REDRAW_NEW_IMAGE;
            }
            $scope.redraw(what_to_redraw, 'empty image loaded');

        });


        $scope.redrawNewImage = function () {
            if (!$scope.state || !$scope.logic || !$scope.logic.img) return null;
            var ctr = $scope.logic.ctr;

            $scope.$element_action_set.css({
                'width': px(ctr.canvas_size[0]), 'height': px(ctr.canvas_size[1]),
                'left': "0px",
                'top': "0px"
            });


            $scope.$canvas.css({
                'width': px(ctr.canvas_size[0]), 'height': px(ctr.canvas_size[1]),
                'left': px(($scope.$container.width() - ctr.canvas_size[0]) / 2),
                'top': px(($scope.$container.height() - ctr.canvas_size[1]) / 2)
            });

        };

        $scope.redrawNewZoom = function () {
            if (!$scope.state || !$scope.logic || !$scope.logic.img || $scope.loading) return null;
            var logic = $scope.logic;

            var state = {zoom: $scope.ngCropZoom, origin: $scope.ngCropOrigin};


            $scope.canvas_for_current_zoom = document.createElement('canvas');

            $scope.canvas_for_current_zoom.width = logic.ctr.canvas_size[0];
            $scope.canvas_for_current_zoom.height = logic.ctr.canvas_size[1];
            if ($scope.ngCropDisabled) {
                $scope.canvas_for_current_zoom.getContext('2d').drawImage($scope.logic.img,
                    0, 0, logic.ctr.image_size[0], logic.ctr.image_size[1],
                    0, 0, logic.ctr.canvas_size[0], logic.ctr.canvas_size[1]);

                $scope.$canvas.css({
                    'background-image': 'url(' + $scope.canvas_for_current_zoom.toDataURL("image/png") + ')',
                    'background-position': 'left 0px top 0px'
                });
            }
            else {
                $scope.canvas_for_current_zoom.getContext('2d').drawImage($scope.logic.img, state.origin[0], state.origin[1],
                    logic.canvas2imgW(logic.ctr.canvas_size[0], state),
                    logic.canvas2imgH(logic.ctr.canvas_size[1], state),
                    0, 0, $scope.canvas_for_current_zoom.width, $scope.canvas_for_current_zoom.height);

                $scope.$canvas.css({
                    'background-image': 'url(' + $scope.canvas_for_current_zoom.toDataURL("image/png") + ')',
                    'background-position': 'left 0px top 0px'
                });
                $scope.$element_action_move.css('background-image', 'url(' + $scope.canvas_for_current_zoom.toDataURL("image/png") + ')');
            }


        }

        $scope.redrawNewRect = function () {

            if (!$scope.state || !$scope.logic || !$scope.logic.img) return null;

            var logic = $scope.logic;
            var state = $scope.state;

            if (!$scope.ngCropDisabled) {
                var state = {zoom: $scope.ngCropZoom, origin: $scope.ngCropOrigin};
                var cr = $scope.logic.img2canvasRect($scope.ngCropCoordinates, state);
                $scope.$element_corners.show();
                $scope.$element_action_move.show();
                $scope.$element_action_set.show();
                $scope.$element_corners.css({left: (cr[0] + cr[2]) / 2, top: (cr[1] + cr[3]) / 2});
                $scope.$element_corners_w.css({left: cr[0]});
                $scope.$element_corners_n.css({top: cr[1]});
                $scope.$element_corners_e.css({left: cr[2]});
                $scope.$element_corners_s.css({top: cr[3]});


                $scope.$element_action_move.css({
                    'left': px(cr[0]),
                    'top': px(cr[1]),
                    'width': px(cr[2] - cr[0]),
                    'height': px(cr[3] - cr[1]),
                    'background-position': 'left ' + px(-1 - logic.img2canvasW($scope.ngCropCoordinates[0] - state.origin[0], state)) +
                    ' top ' + px(-1 - logic.img2canvasH($scope.ngCropCoordinates[1] - state.origin[1], state))
                });
            }
        };

        $scope.redrawNewDisableOrLoading = function () {

            if (!$scope.state || !$scope.logic || !$scope.logic.img || $scope.loading) {
                $scope.$canvas.hide();
                $scope.$loading.show();
            }
            else {
                $scope.$loading.hide();
                $scope.$canvas.show();
                if ($scope.ngCropDisabled) {
                    $scope.$element_corners.hide();
                    $scope.$element_action_move.hide();
                    $scope.$element_action_set.hide();
                }
                else {
                    $scope.$element_corners.show();
                    $scope.$element_action_move.show();
                    $scope.$element_action_set.show();
                }
            }
        }

        $scope.redraw = function (what_to_redraw, why) {
            // console.log(what_to_redraw, why);

            $scope.redrawNewDisableOrLoading();

            if (what_to_redraw === $scope.REDRAW_NEW_IMAGE) {
                $scope.redrawNewImage();
            }

            if (what_to_redraw === $scope.REDRAW_NEW_IMAGE || what_to_redraw === $scope.REDRAW_NEW_ZOOM) {
                $scope.redrawNewZoom();
            }

            if (what_to_redraw === $scope.REDRAW_NEW_IMAGE || what_to_redraw === $scope.REDRAW_NEW_ZOOM || what_to_redraw === $scope.REDRAW_NEW_RECT) {
                $scope.redrawNewRect();
            }

        };


        $scope.mouseRelativeToCanvas = function (event) {
            var of = $scope.$element_action_set.offset();
            return [(event.pageX - of.left) + $(window).scrollLeft(), (event.pageY - of.top) + $(window).scrollTop()];
        };

        $scope.mouseOverCropper = function (event) {
            var of = $scope.$container.offset();
            var ret = [(event.pageX - of.left) + $(window).scrollLeft(), (event.pageY - of.top) + $(window).scrollTop()];
            console.log(ret);
            return (ret[0] >= 0 && ret[1] >= 0 && ret[0] <= $scope.$container.outerWidth() && ret[1] <= $scope.$container.outerHeight()) ? ret : false;
        };

        $scope.zoom_to = function (new_zoomratio, canvas_fixed_point) {


            $scope.processing = true;

            if ($scope.logic.relativeDeviationIn(new_zoomratio, $scope.logic.ctr.max_zoom, 0.01)) new_zoomratio = $scope.logic.ctr.max_zoom;
            if ($scope.logic.relativeDeviationIn(new_zoomratio, $scope.logic.ctr.min_zoom, 0.01)) new_zoomratio = $scope.logic.ctr.min_zoom;
            console.log(canvas_fixed_point);
            var fixed_point = $scope.logic.canvas2imgPoint(canvas_fixed_point, {
                zoom: $scope.ngCropZoom,
                origin: $scope.ngCropOrigin
            });

            $scope.ngCropZoom = new_zoomratio;
            $scope.setZoom(fixed_point);
            $scope.state.zoom = $scope.ngCropZoom;
            $scope.state.coordinates = $scope.ngCropCoordinates;
            $scope.state.origin = $scope.ngCropOrigin;
            $scope.redraw($scope.REDRAW_NEW_ZOOM, 'new zoom');
            $scope.processing = false;
            return true;
        };

        $scope._last_time_called_sr = null;

        $scope.sr = function (r) {
            if ($scope._last_time_called_sr) return null;
            $scope._last_time_called_sr = setTimeout(function () {
                $timeout(function () {
                    $scope._last_time_called_sr = null;
                });
            }, 100);
        };

            // var nowtime = new Date.now? Date.now:Date().getTime();
            // if (nowtime - $scope._last_time_called_sr) {
            //
            // }
            // $scope._last_time_called_sr = nowtime;

        // }, 100);


        $scope.new_rect = function (nr, compass) {
            var state = {zoom: $scope.ngCropZoom, origin: $scope.ngCropOrigin};
            var newir = $scope.logic.fitByConstrains($scope.logic.canvas2imgRect(nr, state), state, compass);

            if (newir) {

                $scope.ngCropCoordinates = newir;

                // $scope.setZoom(fixed_point);
                // $scope.state.zoom = $scope.ngCropZoom;
                $scope.state.coordinates = $scope.ngCropCoordinates;
                // $scope.state.origin = $scope.ngCropOrigin;
                // $scope.redraw($scope.REDRAW_NEW_ZOOM, 'new zoom');
                // $scope.processing = false;
                $scope.sr(newir);
                $scope.redraw($scope.REDRAW_NEW_RECT, 'new rect');


            }
            else {
                return false;
            }
        }


        $scope.addListeners = function () {

            var mm = function (e) {
                if ($scope.ngCropDisabled || $scope.loading) {
                    return false;
                }
                if (!$scope.mouse_clicked) {
                    var canvas_point = $scope.mouseRelativeToCanvas(event);
                    // canvas_point = [canvas_point[0] + $scope.state.x , canvas_point[1] + $scope.state.y];
                    // console.log('mouse position', canvas_point, $scope.logic.canvas2imgPoint(canvas_point, $scope.state));
                    return false;
                }
                var act = $scope.mouse_clicked;
                var current = act[3];
                var mousenow = $scope.mouseRelativeToCanvas(e);
                var dxdy = [mousenow[0] - act[0], mousenow[1] - act[1]];
                var d = [0, 0, 0, 0];
                var compass = createCompass(0.5);
                var newcr = null;

                if (act[2] === 'set') {
                    if (!dxdy[0] || !dxdy[1]) return;
                    if (dxdy[0] >= 0) {
                        d[2] = inRange(dxdy[0], 1, $scope.logic.ctr.canvas_size[0] - current[0]);
                        compass['e'] = 1;
                        compass['w'] = 0;
                    }
                    else {
                        d[0] = inRange(dxdy[0], -current[0], -1);
                        compass['w'] = 1;
                        compass['e'] = 0;
                    }
                    if (dxdy[1] >= 0) {
                        d[3] = inRange(dxdy[1], 1, $scope.logic.ctr.canvas_size[1] - current[1]);
                        compass['s'] = 1;
                        compass['n'] = 0;
                    }
                    else {
                        d[1] = inRange(dxdy[1], -current[1], -1);
                        compass['n'] = 1;
                        compass['s'] = 0;
                    }

                    $scope.new_rect($scope.logic.addDXDY(current, d), compass);

                }
                else if (act[2] === 'move') {
                    d = [inRange(dxdy[0], -current[0], $scope.logic.ctr.canvas_size[0] - current[2]),
                        inRange(dxdy[1], -current[1], $scope.logic.ctr.canvas_size[1] - current[3])];

                    $scope.new_rect($scope.logic.addDXDY(current, d));
                }
                else {
                    var w = current[0] - current[2];
                    var h = current[1] - current[3];

                    if (act[2].indexOf('w') > -1) {
                        d[0] = inRange(dxdy[0], -current[0], -w);
                        compass['w'] = 1;
                        compass['e'] = 0;
                    }
                    else if (act[2].indexOf('e') > -1) {
                        d[2] = inRange(dxdy[0], w, $scope.logic.ctr.canvas_size[0] - current[2]);
                        compass['e'] = 1;
                        compass['w'] = 0;
                    }

                    if (act[2].indexOf('n') > -1) {
                        d[1] = inRange(dxdy[1], -current[1], -h);
                        compass['n'] = 1;
                        compass['s'] = 0;
                    }
                    else if (act[2].indexOf('s') > -1) {
                        d[3] = inRange(dxdy[1], h, $scope.logic.ctr.canvas_size[1] - current[3]);
                        compass['n'] = 0;
                        compass['s'] = 1;
                    }

                    // console.log('scale', current, d, $scope.logic.addDXDY(current, d));
                    $scope.new_rect($scope.logic.addDXDY(current, d), compass);

                    e.preventDefault();
                }
            }

            var mouse_wheeel = function (event) {

                if ($scope.ngCropDisabled || $scope.loading || $scope.processing) {
                    return false;
                }
                var canvas_point = $scope.mouseOverCropper(event);
                console.log(canvas_point);
                if (!canvas_point) return false;
                canvas_point = $scope.mouseRelativeToCanvas(event);
                canvas_point = [inRange(canvas_point[0], 0, $scope.logic.ctr.canvas_size[0]),
                    inRange(canvas_point[1], 0, $scope.logic.ctr.canvas_size[1])]

                event.preventDefault();

                var normalized = 1;

                if (event.wheelDelta) {
                    normalized = (event.wheelDelta % 120 - 0) == -0 ? event.wheelDelta / 120 : event.wheelDelta / 12;
                } else {
                    var rawAmmount = event.deltaY ? event.deltaY : event.detail;
                    normalized = -(rawAmmount % 3 ? rawAmmount * 10 : rawAmmount / 3);
                }


                // return;
                // canvas_point = [canvas_point[0] + $scope.state.x , canvas_point[1] + $scope.state.y];

                var new_zoom = $scope.ngCropZoom * ((normalized > 0) ? 10 / 9 : 9 / 10);

                // var new_zoom_state = $scope.logic.recalculateStateForNewZoom(new_zoom, canvas_point, $scope.state);
                $scope.zoom_to(new_zoom, canvas_point);


            };


            $scope.$element_actions.on('mousedown', function (e) {
                var action = $(this).attr('ng-crop-action');
                var prevrect = $scope.logic.img2canvasRect($scope.ngCropCoordinates, {
                    zoom: $scope.ngCropZoom,
                    origin: $scope.ngCropOrigin
                });
                if (action === 'set') {
                    var pxpy = $scope.mouseRelativeToCanvas(e);
                    prevrect = [pxpy[0], pxpy[1], pxpy[0], pxpy[1]];
                }
                $scope.mouse_clicked = $scope.mouseRelativeToCanvas(e).concat([action, prevrect]);
                e.preventDefault();
            });

            $(window).on('mousemove', mm).on('mouseup', function (e) {
                mm(e);
                $scope.mouse_clicked = false;
            });

            window.addEventListener(('onwheel' in document ? 'wheel' : 'onmousewheel' in document ? 'mousewheel' : 'DOMMouseScroll'), mouse_wheeel);

        }

        $scope.addListeners();

    }


// console.log(angular);

    angular.module('ngCrop', []).directive('ngCrop', function ($compile, $templateCache, $timeout, $q) {
        return {
            restrict: 'A',
            scope: {
                ngCrop: '=ngCrop',
                ngCropCoordinates: '=?ngCropCoordinates',
                ngCropOptions: '=?ngCropOptions',
                ngCropZoom: '=?ngCropZoom',
                ngCropOrigin: '=?ngCropOrigin',
                ngCropLoading: '=?ngCropLoading',
                ngCropDisabled: '=?ngCropDisabled',

                logic: '=?logic',


                ngCropOnError: '&?ngCropOnError',
                ngCropOnLoad: '&?ngCropOnLoad',

            },
            link: function ($scope, element, attrs, model) {
                $scope.onError = function (message) {
                    if ($scope.ngCropOnError()) $scope.ngCropOnError()("" + message);
                    console.error(message);
                }
                $scope.onLoad = function (cropper_logic) {
                    if ($scope.ngCropOnLoad()) $scope.ngCropOnLoad()(cropper_logic);
                    // console.log('img loaded');
                }
                compileTemplate($scope, $compile, element);
                collectElements($scope, element);
                cropLinkFunc($scope, $q, $timeout, element, attrs, model);

            }
        }
    })
})
(this.angular);