(function(angular) {
    "use strict";

    angular.module('FileManagerApp').service('fileNavigator', [
        '$http', 'fileManagerConfig', 'item', function ($http, fileManagerConfig, Item) {

        $http.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';

        var FileNavigator = function(root_id, file_manager_called_for) {
            this.requesting = false;
            this.fileList = [];
            this.search_text = '';
            self.serch_folder = '';
            this.currentPath = [];
            this.searchList = [];
            this.list = [];
            this.root_id = root_id;
            this.ancestors = [root_id];
            this.history = [];
            this.error = '';
            this.search_len = null;
            this.is_search = false;
            this.file_manager_called_for = file_manager_called_for;
        };

            FileNavigator.prototype.getCurrentFolder = function() {
                var self = this;
                return self.ancestors[self.ancestors.length - 1];
            };

        FileNavigator.prototype.setRoot = function(root_id) {
            var self = this;
            self.root_id = root_id;
            self.ancestors = [root_id];
            self.history = [];
            this.fileList = [];
            this.currentPath = [];
            self.goTo(-1);
        };
        FileNavigator.prototype.search = function(query, folder_id, success, error) {
            var self = this;
            var path = self.currentPath.join('/');
            self.search_text = query;
            self.serch_folder = folder_id;
            var data = {params: {
                mode: "list",
                search_text: query,
                root_id: self.root_id,
                file_manager_called_for: self.file_manager_called_for,
                folder_id: folder_id //? folder_id : self.ancestors[self.ancestors.length - 1]
            }};
            self.requesting = true;
            self.is_search = true;
            self.searchList = [];
            self.error = '';
            self.list = [];
            $http.post(fileManagerConfig.listUrl, data).success(function(resp) {
                self.searchList = [];
                self.ancestors = resp.data.ancestors;
                angular.forEach(resp.data.list, function(file) {
                    self.searchList.push(new Item(file, self.currentPath));
                });
                self.list = self.searchList;
                self.search_len = self.searchList.length;
                self.requesting = false;
                if (resp.error) {
                    self.error = resp.error;
                    return typeof error === 'function' && error(resp);
                }
                typeof success === 'function' && success(resp);
            }).error(function(data) {
                self.requesting = false;
                typeof error === 'function' && error(data);
            });
        };

        FileNavigator.prototype.refresh = function(folder_id, success, error) {
            var self = this;
            var path = self.currentPath.join('/');
            var data = {params: {
                mode: "list",
                onlyFolders: false,
                search_text: '',
                path: '/' + path,
                file_manager_called_for: self.file_manager_called_for,
                root_id: self.root_id,
                folder_id: folder_id ? folder_id : self.ancestors[self.ancestors.length - 1]
            }};
            self.is_search  = false;
            self.searchList = [];
            self.requesting = true;
            self.fileList = [];
            self.error = '';
            self.list = [];
            $http.post(fileManagerConfig.listUrl, data).success(function(resp) {
                self.fileList = [];
                self.ancestors = resp.data.ancestors;
                angular.forEach(resp.data.list, function(file) {
                    self.fileList.push(new Item(file, self.currentPath));
                });
                self.list = self.fileList;
                self.requesting = false;
                self.buildTree(path);
                if (resp.error) {
                    self.error = resp.error;
                    return typeof error === 'function' && error(resp);
                }
                typeof success === 'function' && success(resp);
            }).error(function(data) {
                self.requesting = false;
                typeof error === 'function' && error(data);
            });
        };

        FileNavigator.prototype.buildTree = function(path) {
            var self = this;
            function recursive(parent, item, path) {
                var absName = path ? (path + '/' + item.model.name) : item.model.name;
                if (parent.name.trim() && path.trim().indexOf(parent.name) !== 0) {
                    parent.nodes = [];
                }
                if (parent.name !== path) {
                    for (var i in parent.nodes) {
                        recursive(parent.nodes[i], item, path);
                    }
                } else {
                    for (var e in parent.nodes) {
                        if (parent.nodes[e].name === absName) {
                            return;
                        }
                    }
                    parent.nodes.push({item: item, name: absName, nodes: []});
                }
                parent.nodes = parent.nodes.sort(function(a, b) {
                    return a.name < b.name ? -1 : a.name === b.name ? 0 : 1;
                });
            };

            !self.history.length && self.history.push({name: path, nodes: []});
            for (var o in self.fileList) {
                var item = self.fileList[o];
                item.isFolder() && recursive(self.history[0], item, path);
            }
        };

        FileNavigator.prototype.folderClick = function(item) {
            var self = this;
            if(self.fileList === 0){
                return false
            }
            self.currentPath = [];
            if (item && item.isFolder()) {
                self.currentPath = item.model.fullPath().split('/').splice(1);
                //self.currentPath.push(item.model.name);
                self.refresh(item.model.id, function () {
                });
            }else{
                self.buildTree('/');
                self.goTo(-1)
            }

        };

        FileNavigator.prototype.parent = function() {
            return this.fileList[this.fileList.length - 1]
        };

        FileNavigator.prototype.upDir = function() {
            var self = this;
            if((self.search_text.length>0 && self.currentPath[0]) && self.currentPath !== self.serch_folder){
                if(self.ancestors.length > 2 || self.ancestors.indexOf(self.serch_folder) <= -1){
                    self.search_text = self.ancestors.indexOf(self.serch_folder) <= -1 ? '': self.search_text;
                    self.currentPath = self.currentPath.slice(0, -1);
                    self.ancestors = self.ancestors.slice(0, -1);
                    self.refresh()
                }else{
                    self.currentPath = self.currentPath.slice(0, -1);
                    self.ancestors = self.ancestors.slice(0, -1);
                    self.search(self.search_text, self.serch_folder);
                }
            }else if(self.currentPath[0]) {
                self.currentPath = self.currentPath.slice(0, -1);
                self.ancestors = self.ancestors.slice(0, -1);
                self.refresh();
            }
        };

        FileNavigator.prototype.goTo = function(index) {
            var self = this;
            if(index === -1 && self.history.length>0){
                self.buildTree('/');
            }
            $('.navbar-right').find('input[type=text]').val('');
            self.search_text = '';
            self.currentPath = self.currentPath.slice(0, index + 1);
            self.ancestors = self.ancestors.slice(0, index + 2);
            self.refresh();
        };

        FileNavigator.prototype.fileNameExists = function(fileName) {
            var self = this;
            for (var i in self.fileList) {
                i = self.fileList[i];
                if (i.model.name.trim() === fileName.trim()) {
                    return true;
                }
            }
        };

        FileNavigator.prototype.listHasFolders = function() {
            var self = this;
            for (var item in self.fileList) {
                if (self.fileList[item].model.type === 'dir') {
                    return true;
                }
            }
        };

        return FileNavigator;
    }]);
})(angular);