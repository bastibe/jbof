classdef DataSet < handle
%DataSet is a structured collection of Items that contain data.
%
%   DataSet(directory) reads the dataset in directory. This operation
%   is free, no data is read until items are requested.
%
%   DataSet(directory, readonly) is currently not implemented.
%   DataSets are currently always read-only.
%
%   A DataSet has two properties:
%   - metadata, a struct containing DataSet metadata
%   - name, the name of the parent directory
%
%   A DataSet contains Items, which are subdirectories of the DataSet.
%   Each Item again has two properties:
%   - metadata, a struct containing Item metadata
%   - name, the name of the subdirectory
%   Each Item contains data arrays, as files with the subdirectory.
%
%   Use allItems() to get an array of all items. Use hasItem() and
%   getItem() to access items by name. Use findItems() and
%   findOneItem() to access items by metadata search.
%
%   Use Item.allArrays() to get a struct of all data arrays and their
%   metadata. Use Item.hasArray() and Item.getArray() to access data
%   arrays by name.

% Copyright (C) 2019 Bastian Bechtold
%
% This program is free software: you can redistribute it and/or modify
% it under the terms of the GNU General Public License as published by
% the Free Software Foundation, either version 3 of the License, or
% (at your option) any later version.
%
% This program is distributed in the hope that it will be useful, but
% WITHOUT ANY WARRANTY; without even the implied warranty of
% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
% General Public License for more details.
%
% For the full text of the GNU General Public License, see
% <https://www.gnu.org/licenses/>.

    properties (Hidden)
        directory
        readonly
        cache
    end

    properties (Dependent)
        metadata
        name
    end

    methods
        function obj = DataSet(directory, readonly)
            obj.directory = directory;
            if exist("readonly") && ~isempty(readonly) && islogical(readonly)
                obj.readonly = readonly;
            else
                obj.readonly = true;
            end
            if ~isfolder(obj.directory)
                error(sprintf("DataSet directory %s does not exist", obj.directory));
            elseif ~isfile(fullfile(obj.directory, "_metadata.json"))
                error(sprintf("%s does not seem to be a DataSet", obj.directory));
            elseif ~obj.readonly
                error("JBOF on Matlab currently does not support writing to DataSets");
            end
        end

        function name = get.name(obj)
            [~, name, ~] = fileparts(obj.directory);
        end

        function metadata = get.metadata(obj)
            metadata = jsondecode(fileread(fullfile(obj.directory, "_metadata.json")));
            metadata = rmfield(metadata, "x_itemformat");
        end

        function items = allItems(obj)
            % Get an array of all the Items in the DataSet
            %
            % For large DataSets, this will be slow the first time,
            % but faster for subsequent times, as items are cached.

            if isempty(obj.cache)
                cache = jbof.Item.empty();
                allFiles = dir(obj.directory);
                for fileIdx = 1:length(allFiles)
                    fileStruct = allFiles(fileIdx);
                    if ~fileStruct.isdir || fileStruct.name == "." || fileStruct.name == ".."
                        continue
                    end
                    cache(end+1) = jbof.Item(fullfile(obj.directory, fileStruct.name), obj.readonly);
                end
                obj.cache = cache;
            end
            items = obj.cache;
        end

        function items = findItems(obj, varargin)
            % Search for Items that match a metadata query
            %
            % Queries can be arbitrary key-value pairs that are
            % matched in the Item metadata.
            %
            % If there are many items, the first run might be slow,
            % but subsequent findItems() will search through cached
            % metadata, and will run faster.

            if mod(length(varargin), 2) ~= 0
                error("findItems must ne called with an even number of arguments")
            end
            allItems = obj.allItems();
            items = jbof.Item.empty();
            for itemIdx = 1:length(allItems)
                item = allItems(itemIdx);
                useItem = true;
                metadata = item.metadata;
                for argIdx = 1:2:length(varargin)
                    if ~isfield(metadata, varargin{argIdx})
                        useItem = false;
                        break
                    end
                    if ~(isequal(varargin{argIdx+1}, metadata.(varargin{argIdx})))
                        useItem = false;
                        break
                    end
                end
                if useItem
                    items(end+1) = item;
                end
            end
        end

        function item = findOneItem(obj, varargin)
            % Search for one Item that matches a metadata query
            %
            % see findItems for details.

            if mod(length(varargin), 2) ~= 0
                error("findItems must ne called with an even number of arguments")
            end
            allItems = obj.allItems();
            items = jbof.Item.empty();
            for itemIdx = 1:length(allItems)
                item = allItems(itemIdx);
                useItem = true;
                metadata = item.metadata;
                for argIdx = 1:2:length(varargin)
                    if ~isfield(metadata, varargin{argIdx})
                        useItem = false;
                        break
                    end
                    if ~(isequal(varargin{argIdx+1}, metadata.(varargin{argIdx})))
                        useItem = false;
                        break
                    end
                end
                if useItem
                    return
                end
            end
        end

        function yesNo = hasItem(obj, name)
            % Check if item of name exists.
            yesNo = isfolder(fullfile(obj.directory, name));
        end

        function item = getItem(obj, name)
            % Get item by name.
            if ~obj.hasItem(name)
                error(sprintf("No item %s", name));
            end
            item = jbof.Item(fullfile(obj.directory, name), obj.readonly);
        end

        %% Not implemented:

        function item = addItem(obj, name, metadata)
            error("Not implemented")
        end

        function deleteItem(obj, item)
            error("Not implemented")
        end

        function hash = calculateHash(obj)
            error("Not implemented")
        end
    end
end
