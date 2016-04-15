(function(window, angular, $) {
    "use strict";
    angular.module('FileManagerApp').factory('item', ['$http', '$translate','$cookies', 'fileManagerConfig', 'chmod', function($http, $cookies, $translate, fileManagerConfig, Chmod) {

        var Item = function(model, path) {
            var rawModel = {
                name: model && model.name || '',
                author_name: model && model.author_name || '',
                description: model && model.description || '',
                add_all: model && model.add_all || '',
                path: path || [],
                path_to: model && model.path_to || '',
                type: model && model.type || 'file',
                youtube_data: model && model.youtube_data || {},
                size: model && model.size || 0,
                date: convertDate(model && model.date),
                perms: new Chmod(model && model.rights),
                content: model && model.content || '',
                actions: model && model.actions || {},
                id: model && model.id || '',
                parent_id: model && model.parent_id || '',
                recursive: false,
                url: model && model.url || '',
                file_url: model && model.file_url || '',
                sizeKb: function() {
                    return Math.round(this.size / 1024, 1);
                },
                fullPath: function() {
                    return ('/' + this.path.join('/') + '/' + this.name).replace(/\/\//, '/');
                }
            };

            this.error = '';
            this.inprocess = false;

            this.model = angular.copy(rawModel);
            this.tempModel = angular.copy(rawModel);

            function convertDate(mysqlDate) {
                var d = (mysqlDate || '').toString().split(/[- :]/);
                return new Date(d[0], d[1] - 1, d[2], d[3], d[4], d[5]);
            }
        };

        Item.prototype.update = function() {
            angular.extend(this.model, angular.copy(this.tempModel));
            return this;
        };

        Item.prototype.revert = function() {
            angular.extend(this.tempModel, angular.copy(this.model));
            this.error = '';
            return this;
        };

        Item.prototype.defineCallback = function(data, success, error) {
            /* Check if there was some error in a 200 response */
            var self = this;
            if (data.result && data.result.error) {
                self.error = data.result.error;
                return typeof error === 'function' && error(data);
            }
            if (data.error) {
                self.error = data.error.message;
                return typeof error === 'function' && error(data);
            }
            self.update();
            return typeof success === 'function' && success(data);
        };

        Item.prototype.createFolder = function(success, error) {
            var self = this;
            var data = {params: {
                mode: "addfolder",
                path: self.tempModel.path.join('/'),
                name: self.tempModel.name,
                root_id: self.tempModel.root_id,
                folder_id: self.tempModel.folder_id
            }};

            if (self.tempModel.name.trim()) {
                self.inprocess = true;
                self.error = '';
                return $http.post(fileManagerConfig.createFolderUrl, data).success(function(data) {
                    self.defineCallback(data, success, error);
                }).error(function(data) {
                    self.error = data.result && data.result.error ?
                        data.result.error:
                        $translate.instant('error_creating_folder');
                    typeof error === 'function' && error(data);
                })['finally'](function() {
                    self.inprocess = false;
                });
            }
        };

        Item.prototype.set_properties = function(success, error) {
            var self = this;
            var data = {params: {
                "id" : self.model.id,
                'add_all': self.tempModel.add_all,
                "name": self.tempModel.name.trim() === self.model.name.trim() ? 'None': self.tempModel.name.trim(),
                "author_name": self.tempModel.author_name === ''? '':self.tempModel.author_name,
                "description": self.tempModel.description === ''? '':self.tempModel.description,
                "mode": "properties",
                "path": self.model.fullPath(),
                "newPath": self.tempModel.fullPath()
            }};
            if (self.tempModel.name.trim()) {
                self.inprocess = true;
                self.error = '';
                return $http.post(fileManagerConfig.set_properties, data).success(function(data) {
                    self.defineCallback(data, success, error);
                }).error(function(data) {
                    self.error = data.result && data.result.error ?
                        data.result.error:
                        $translate.instant('error_set_properties');
                    typeof error === 'function' && error(data);
                })['finally'](function() {
                    self.inprocess = false;
                });
            }
        };

        Item.prototype.cut = function(success, error){
            var self = this;



            var id = $cookies.cut_file_id = self.model.id;
        };

        Item.prototype.copy = function(success, error){
            var self = this;
            var id = $cookies.copy_file_id = self.model.id;
        };

        Item.prototype.paste = function(success, error) {
            var self = this;
            var parent_id = '';
            if(self.model.id === self.tempModel.id){
                parent_id = self.tempModel.folder_id;
            }else if(self.isFolder() && self.tempModel.len !== 0){
                parent_id = self.model.id;
            }else{
                parent_id =  self.tempModel.folder_id;
            }
            var data = {params: {
                id: self.tempModel.id,
                mode: "paste",
                path: self.model.fullPath(),
                folder_id: parent_id
            }};
            self.inprocess = true;
            self.error = '';
            if(self.tempModel.mode == 'copy') {
                return $http.post(fileManagerConfig.copyUrl, data).success(function (data) {
                    self.er = data.data === false ? self.tempModel.time_o: null;
                    self.error = data.data === '' ? self.tempModel.error: null;
                    self.defineCallback(data, success, error);
                }).error(function(data) {
                    self.error = data.result && data.result.error ?
                        data.result.error:
                    typeof error === 'function' && error(data);
                })['finally'](function() {
                    self.inprocess = false;
                });
            }else{
                return $http.post(fileManagerConfig.cutUrl, data).success(function (data) {
                    self.er = data.data === false ? self.tempModel.time_o: null;
                    self.error = data.data === false ? self.tempModel.error: null;
                    self.defineCallback(data, success, error);
                }).error(function(data) {
                    self.error = data.result && data.result.error ?
                        data.result.error:
                        $translate.instant('error_cut');
                    typeof error === 'function' && error(data);
                })['finally'](function() {
                    self.inprocess = false;
                });
            }
        };

        Item.prototype.compress = function(success, error) {
            var self = this;
            var data = {params: {
                mode: "compress",
                path: self.model.fullPath(),
                destination: self.tempModel.fullPath()
            }};
            if (self.tempModel.name.trim()) {
                self.inprocess = true;
                self.error = '';
                return $http.post(fileManagerConfig.compressUrl, data).success(function(data) {
                    self.defineCallback(data, success, error);
                }).error(function(data) {
                    self.error = data.result && data.result.error ?
                        data.result.error:
                        $translate.instant('error_compressing');
                    typeof error === 'function' && error(data);
                })['finally'](function() {
                    self.inprocess = false;
                });
            }
        };

        Item.prototype.extract = function(success, error) {
            var self = this;
            var data = {params: {
                mode: "extract",
                path: self.model.fullPath(),
                sourceFile: self.model.fullPath(),
                destination: self.tempModel.fullPath()
            }};

            self.inprocess = true;
            self.error = '';
            return $http.post(fileManagerConfig.extractUrl, data).success(function(data) {
                self.defineCallback(data, success, error);
            }).error(function(data) {
                self.error = data.result && data.result.error ?
                    data.result.error:
                    $translate.instant('error_extracting');
                typeof error === 'function' && error(data);
            })["finally"](function() {
                self.inprocess = false;
            });
        };

        Item.prototype.download = function() {
            var self = this;
            var url = self.fileUrl(self.model.id, true);
            if (self.model.type !== 'dir') {
                window.open(url, '_blank', '');
            }
        };

        Item.prototype.fileUrl = function(id, down, if_no_file){
            return fileUrl(id, down, if_no_file)
        };

        Item.prototype.choose = function() {
            return true;
        };

        Item.prototype.preview = function() {
            var self = this;
            return self.download(true);
        };

        Item.prototype.getContent = function(success, error) {
            var self = this;
            var data = {params: {
                mode: "editfile",
                path: self.tempModel.fullPath()
            }};
            self.inprocess = true;
            self.error = '';
            return $http.post(fileManagerConfig.getContentUrl, data).success(function(data) {
                self.tempModel.content = self.model.content = data.result;
                self.defineCallback(data, success, error);
            }).error(function(data) {
                self.error = data.result && data.result.error ?
                    data.result.error:
                    $translate.instant('error_getting_content');
                typeof error === 'function' && error(data);
            })['finally'](function() {
                self.inprocess = false;
            });
        };

        Item.prototype.remove = function(success, error) {
            var self = this;
            var data = {params: {
                mode: "delete",
                path: self.tempModel.fullPath()
            }};
            self.inprocess = true;
            self.error = '';
            return $http.post(fileManagerConfig.removeUrl+self.model.id, data).success(function(data) {
                if(data.data.error){
                    self.error = data.data.error
                }else{
                   self.defineCallback(data, success, error);
                }

            }).error(function(data) {
                self.error = data.result && data.result.error ?
                    data.result.error:
                    self.tempModel.error;
                typeof error === 'function' && error(data);
            })['finally'](function() {
                self.inprocess = false;
            });
        };

        Item.prototype.edit = function(success, error) {
            var self = this;
            var data = {params: {
                mode: "savefile",
                content: self.tempModel.content,
                path: self.tempModel.fullPath()
            }};
            self.inprocess = true;
            self.error = '';

            return $http.post(fileManagerConfig.editUrl, data).success(function(data) {
                self.defineCallback(data, success, error);
            }).error(function(data) {
                self.error = data.result && data.result.error ?
                    data.result.error:
                    $translate.instant('error_modifying');
                typeof error === 'function' && error(data);
            })['finally'](function() {
                self.inprocess = false;
            });
        };

        Item.prototype.changePermissions = function(success, error) {
            var self = this;
            var data = {params: {
                mode: "changepermissions",
                path: self.tempModel.fullPath(),
                perms: self.tempModel.perms.toOctal(),
                permsCode: self.tempModel.perms.toCode(),
                recursive: self.tempModel.recursive
            }};
            self.inprocess = true;
            self.error = '';
            return $http.post(fileManagerConfig.permissionsUrl, data).success(function(data) {
                self.defineCallback(data, success, error);
            }).error(function(data) {
                self.error = data.result && data.result.error ?
                    data.result.error:
                    $translate.instant('error_changing_perms');
                typeof error === 'function' && error(data);
            })['finally'](function() {
                self.inprocess = false;
            });
        };

        Item.prototype.canPaste = function(id, folder_id){
            var data = {params: {
                perms: self.tempModel.perms.toOctal(),
                permsCode: self.tempModel.perms.toCode(),
                recursive: self.tempModel.recursive
            }};
            return $http.post(fileManagerConfig.can_paste, data).success(function(data) {
                self.defineCallback(data, success, error);
            })
        };
        Item.prototype.title = function(){
            var size = this.isFolder()? '':'('+this.model.sizeKb()+')kb';
            var p = this.model.path_to;
            return 'Name: ' + this.model.name + size + '\n'+ 'Full path: '+p
        };

        Item.prototype.isFolder = function() {
            return this.model.type === 'dir';
        };

        Item.prototype.isEditable = function() {
            return !this.isFolder() && fileManagerConfig.isEditableFilePattern.test(this.model.name);
        };

        Item.prototype.isImage = function() {
            return fileManagerConfig.isImageFilePattern.test(this.model.name);
        };

        Item.prototype.actionAllowed = function(action) {
            return true;
        };

        Item.prototype.isCompressible = function() {
            return this.isFolder();
        };

        Item.prototype.isExtractable = function() {
            return !this.isFolder() && fileManagerConfig.isExtractableFilePattern.test(this.model.name);
        };

        return Item;
    }]);
})(window, angular, jQuery);
