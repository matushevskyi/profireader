'use strict';

var gulp = require('gulp');
var del = require('del');

var less = require('gulp-less-sourcemap');
var path = require('path');

// Vars
var src = 'bower_components/';
var src_dev = 'bower_components_dev/';
var dst = 'new/';

var watch = require('gulp-watch');
var runSequence = require('run-sequence');
var gutil = require('gulp-util');
var taskListing = require('gulp-task-listing');

//var ext_replace = require('gulp-ext-replace');

gulp.task('clean', function (cb) {
//    del([
//        'filemanager/*',
//    ], cb);
});

gulp.task('install_filemanager', function () {
    return gulp.src(src_dev + 'angular-server-driven-filemanager/dist/*')
        .pipe(gulp.dest(dst + 'filemanager/'));
});

gulp.task('install_fileuploader', function () {
    return gulp.src(src + 'ng-file-upload/ng-file-upload.min.js')
        .pipe(gulp.dest(dst + 'fileuploader/'));
});

gulp.task('install_angular', function () {
    return gulp.src(src + 'angular/angular.min.js')
        .pipe(gulp.dest(dst + 'angular/'));
});

gulp.task('install_angular_translate', function () {
    return gulp.src(src + 'angular-translate/angular-translate.min.js')
        .pipe(gulp.dest(dst + 'angular/'));
});

gulp.task('install_angular_cookies', function () {
    return gulp.src(src + 'angular-cookies/angular-cookies.min.js')
        .pipe(gulp.dest(dst + 'angular/'));
});

gulp.task('install_angular_animate', function () {
    return gulp.src(src + 'angular-animate/angular-animate.min.js')
        .pipe(gulp.dest(dst + 'angular-animate/'));
});

gulp.task('install_angular_bootstrap', function () {
    return gulp.src([src + 'angular-bootstrap/ui-bootstrap.min.js', src + 'angular-bootstrap/ui-bootstrap-tpls.min.js'])
        .pipe(gulp.dest(dst + 'angular-bootstrap/'));
});

gulp.task('install_angular_ui_tinymce', function () {
    return gulp.src(src + 'angular-ui-tinymce/src/tinymce.js')
        .pipe(gulp.dest(dst + 'angular-ui-tinymce/'));
});

gulp.task('install_angular_ui_select', function () {
    return gulp.src(src + 'angular-ui-select/dist/select.min.*')
        .pipe(gulp.dest(dst + 'angular-ui-select/'));
});


gulp.task('install_tinymce', function () {
    return gulp.src(src + 'tinymce-dist/tinymce.jquery.min.js')
        .pipe(gulp.dest(dst + 'tinymce/'));
});

gulp.task('install_datepicker', function () {
    return gulp.src([src + 'angular-ui-slider/src/slider.js'])
        .pipe(gulp.dest(dst + 'angular-ui-slider/'));
});

gulp.task('install_angular_crop', function () {
    return gulp.src([src_dev + 'ng-crop/ng-crop.*'])
        .pipe(gulp.dest(dst + 'angular-crop/'));
});

gulp.task('install_angular_xeditable', function () {
    return gulp.src([src + 'angular-xeditable/dist/css/xeditable.css', src + 'angular-xeditable/dist/js/xeditable.js'])
        .pipe(gulp.dest(dst + 'angular-xeditable/'));
});

// gulp.task('install_cropper', function () {
//     return gulp.src([src + 'cropper/dist/cropper.css', src + 'cropper/dist/cropper.js'])
//         .pipe(gulp.dest(dst + 'cropper/'));
// });

gulp.task('install_cropper', function () {
    return gulp.src(['bower_components_dev/ng-crop/src/*'])
        .pipe(gulp.dest(dst + 'ng-crop/'));
});

gulp.task('install_slider', function () {
    return gulp.src([src + 'angular-ui-slider/src/slider.js'])
        .pipe(gulp.dest(dst + 'angular-ui-slider/'));
});

gulp.task('install_bootstrap', function () {
    return gulp.src([src + 'bootstrap/dist/**/*'])
        .pipe(gulp.dest(dst + 'bootstrap/'));
});

gulp.task('less', function () {
    var layouts = ['spring', 'bird', 'forester'];

    var dirs = ['./css/*.less', ];
    for (var i = 0; i < layouts.length; i++) {
        dirs.push('./front/' + layouts[i] + '/css/*.less');
    }

    for (var i = 0; i < dirs.length; i++) {
        gutil.log(gutil.colors.yellow('recompiling ' + ' (' + dirs[i] +  ')'));
        gulp.src(dirs[i])
        .pipe(less({
            sourceMap: {
                sourceMapRootpath: dirs[i].replace(/\/[^\/]*$/, '')
            }
        }))
        .pipe(gulp.dest(dirs[i].replace(/\/[^\/]*$/,'')));
    }

    gulp.watch(dirs).on('change', function(file) {
        gutil.log(gutil.colors.yellow('JS changed' + ' (' + file.path.replace(/.less$/, '.css,.map') +' created)'));
        gulp.src(file.path)
        .pipe(less({
            sourceMap: {
                sourceMapRootpath: file.path.replace(/.less$/, '')
            }
        }))
        .pipe(gulp.dest(file.path.replace(/\/[^\/]*$/,'')));
    })

});

gulp.task('install_jquery_datetimepicker', function () {
    return gulp.src([src + 'jquery-datetimepicker/jquery.datetimepicker.*'])
        .pipe(gulp.dest(dst + 'jquery-datetimepicker/'));
});

gulp.task('install_eonasdan-bootstrap-datetimepicker', function () {
    return gulp.src([src + 'eonasdan-bootstrap-datetimepicker/build/js/bootstrap-datetimepicker.min.js',
    src + 'eonasdan-bootstrap-datetimepicker/build/css/bootstrap-datetimepicker.min.css'])
        .pipe(gulp.dest(dst + 'eonasdan-bootstrap-datetimepicker/'));
});

gulp.task('install_moment', function () {
    return gulp.src([src + 'moment/min/moment.min.js', src + 'moment/locale/uk.js'])
        .pipe(gulp.dest(dst + 'moment/'));
});


gulp.task('default', taskListing);

gulp.task('all', ['install_fileuploader', 'install_angular', 'install_angular_translate', 'install_angular_cookies',
    'install_angular_ui_select',
    'install_angular_crop',
'install_angular_ui_tinymce', 'install_tinymce', 'install_angular_bootstrap', 'install_angular_animate', 'install_cropper',
'install_slider','install_bootstrap', 'install_angular_crop', 'install_eonasdan-bootstrap-datetimepicker', 'install_moment']);

