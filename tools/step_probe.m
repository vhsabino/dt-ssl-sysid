function T = step_probe(stepFile, varargin)
%STEP_PROBE  Bounding boxes of every leaf part of a STEP (AP214/AP242) assembly, in the file frame.
%
%   T = STEP_PROBE(file) parses the STEP text directly (no CAD kernel): it follows the
%   NEXT_ASSEMBLY_USAGE_OCCURRENCE tree, composes the ITEM_DEFINED_TRANSFORMATION of every
%   occurrence and collects, per leaf solid, the B-rep vertices plus sample points along circular
%   edges (arcs only; B-spline control points are ignored: they can lie far off the solid).  Points are expressed
%   in the frame of the top-level product of the file (for a sub-assembly exported on its own that
%   is the sub-assembly origin; for a part or a Simplify/Derive output made from the robot assembly
%   it is the robot frame).  Free-form (B-spline) edges are bounded only by their end vertices.
%
%   Units are the file units (Inventor -> mm).  The output table has one row per leaf occurrence
%   (path, n points, lo, hi, size) plus a last row 'ASSEMBLY' with the union.  Optional name/value:
%     'Transform', M   4x4 matrix applied to every point before the statistics (e.g. the dtssl
%                      USD -> MJCF map: x' = -y, y' = x, z' = z - 24.15 mm; see tools/usd_to_mjcf_meshes.py)
%     'Quiet', true    do not print the table
%     'SolidsOnly', tf true (default): only MANIFOLD_SOLID_BREP / BREP_WITH_VOIDS bodies are measured;
%                      false also follows sheet bodies and other representation items (an Inventor
%                      Simplify export carries construction sheets far outside the part)
%
%   Validated (2026-09-28) on kicker_assembly_front.stp, kicker_assembly_chip.stp and
%   Dribbler_Robocup2025v3.stp of usd/cad (Inventor 2025, AP242) and on cad/chasis_simplified_Simplify_2.stp
%   (x' in [-88.0, 76.5] mm after the MJCF transform, as meshes.json).  Not a general STEP reader:
%   MAPPED_ITEM instancing, non-identity child placements other than AXIS2_PLACEMENT_3D and
%   surface extents beyond edges/control points are not handled.
%
%   Example (bounding boxes in the dtssl MJCF body frame, mm):
%     Rz = [0 -1 0 0; 1 0 0 0; 0 0 1 -24.15; 0 0 0 1];
%     step_probe('cad\chasis_simplified_Simplify_2.stp', 'Transform', Rz);

ip = inputParser;
ip.addParameter('Transform', eye(4), @(m) isequal(size(m), [4 4]));
ip.addParameter('Quiet', false, @islogical);
ip.addParameter('SolidsOnly', true, @islogical);
ip.parse(varargin{:});
Tx = ip.Results.Transform;

txt = fileread(stepFile);
i0 = strfind(txt, 'DATA;'); txt = txt(i0(1):end);
txt = regexprep(txt, '\r?\n', '');
ent = regexp(txt, '#(\d+)=([^;]*);', 'tokens');
ids = cellfun(@(c) str2double(c{1}), ent);
N = max(ids);
typ = repmat({''}, N, 1); args = repmat({''}, N, 1); refs = cell(N, 1);
for k = 1:numel(ids)
    b = ent{k}{2}; id = ids(k);
    if b(1) == '('
        typ{id} = 'COMPLEX'; args{id} = b;
    else
        p = find(b == '(', 1); typ{id} = b(1:p-1); args{id} = b(p:end);
    end
    r = regexp(b, '#(\d+)', 'tokens'); refs{id} = cellfun(@(c) str2double(c{1}), r);
end

pts = nan(N, 3); dirs = nan(N, 3);
for id = find(strcmp(typ, 'CARTESIAN_POINT'))'
    v = regexp(args{id}, '\(([-+0-9.Ee]+),([-+0-9.Ee]+),([-+0-9.Ee]+)\)', 'tokens');
    if ~isempty(v), pts(id, :) = str2double(v{1}); end
end
for id = find(strcmp(typ, 'DIRECTION'))'
    v = regexp(args{id}, '\(([-+0-9.Ee]+),([-+0-9.Ee]+),([-+0-9.Ee]+)\)', 'tokens');
    if ~isempty(v), dirs(id, :) = str2double(v{1}); end
end

P = cell(N, 1);                                   % AXIS2_PLACEMENT_3D -> homogeneous 4x4
for id = find(strcmp(typ, 'AXIS2_PLACEMENT_3D'))'
    rr = refs{id}; o = pts(rr(1), :); z = [0 0 1]; x = [1 0 0];
    if numel(rr) >= 2, z = dirs(rr(2), :); end
    if numel(rr) >= 3, x = dirs(rr(3), :); end
    z = z / norm(z); x = x - dot(x, z) * z; x = x / norm(x); y = cross(z, x);
    P{id} = [x' y' z' o'; 0 0 0 1];
end

% occurrences: NAUO -> PRODUCT_DEFINITION_SHAPE -> CONTEXT_DEPENDENT_SHAPE_REPRESENTATION
%   -> (REPRESENTATION_RELATIONSHIP(child rep, parent rep) ..._WITH_TRANSFORMATION(IDT))
%   IDT(item1 in child rep, item2 in parent rep): child points map as P(item2) * inv(P(item1))
pdsOfNauo = zeros(N, 1);
for id = find(strcmp(typ, 'PRODUCT_DEFINITION_SHAPE'))'
    rr = refs{id};
    if ~isempty(rr) && strcmp(typ{rr(1)}, 'NEXT_ASSEMBLY_USAGE_OCCURRENCE'), pdsOfNauo(rr(1)) = id; end
end
rrOfPds = zeros(N, 1);
for id = find(strcmp(typ, 'CONTEXT_DEPENDENT_SHAPE_REPRESENTATION'))'
    rr = refs{id}; rrOfPds(rr(2)) = rr(1);
end
nauo = find(strcmp(typ, 'NEXT_ASSEMBLY_USAGE_OCCURRENCE'))';
occ = struct('name', {}, 'parent', {}, 'child', {}, 'T', {}, 'rep', {});
for id = nauo
    nm = regexp(args{id}, '''([^'']*)''', 'tokens'); nm = nm{2}{1};
    rr = refs{id};
    rrefs = refs{rrOfPds(pdsOfNauo(id))};             % [child rep, parent rep, IDT]
    it = refs{rrefs(3)};                              % [item1 (child), item2 (parent)]
    occ(end+1) = struct('name', nm, 'parent', rr(1), 'child', rr(2), 'T', P{it(2)} / P{it(1)}, 'rep', rrefs(1)); %#ok<AGROW>
end

% representations related by a plain SHAPE_REPRESENTATION_RELATIONSHIP (e.g. the placement-only
% SHAPE_REPRESENTATION of a part and its ADVANCED_BREP_SHAPE_REPRESENTATION) share their items
related = cell(N, 1);
for id = find(strcmp(typ, 'SHAPE_REPRESENTATION_RELATIONSHIP'))'
    rr = refs{id};
    if numel(rr) == 2, related{rr(1)} = [related{rr(1)} rr(2)]; related{rr(2)} = [related{rr(2)} rr(1)]; end
end
itemsOf = @(rep) unique([refs{rep} refs{related{rep}}]);

rows = {};
allP = zeros(0, 3);
if isempty(occ)                                       % single part: every solid of every shape rep
    reps = find(strcmp(typ, 'SHAPE_REPRESENTATION') | strcmp(typ, 'ADVANCED_BREP_SHAPE_REPRESENTATION'))';
    stack = struct('items', {unique([refs{reps}])}, 'T', eye(4), 'path', '/');
else
    parents = [occ.parent]; children = [occ.child];
    root = setdiff(unique(parents), unique(children));
    stack = struct('items', {[]}, 'T', eye(4), 'path', ''); stack(1) = [];
    queue = struct('pd', root(1), 'T', eye(4), 'path', '');
    while ~isempty(queue)
        s = queue(end); queue(end) = [];
        for oi = find(parents == s.pd)
            o = occ(oi); Tl = s.T * o.T; path = [s.path '/' o.name];
            if any(parents == o.child)
                queue(end+1) = struct('pd', o.child, 'T', Tl, 'path', path); %#ok<AGROW>
            else
                stack(end+1) = struct('items', {itemsOf(o.rep)}, 'T', Tl, 'path', path); %#ok<AGROW>
            end
        end
    end
end

skip = {'AXIS2_PLACEMENT_3D', 'COMPLEX', 'GEOMETRIC_REPRESENTATION_CONTEXT'};
solids = {'MANIFOLD_SOLID_BREP', 'BREP_WITH_VOIDS'};
for si = 1:numel(stack)
    s = stack(si);
    items = s.items; items = items(items >= 1 & items <= N);
    if ip.Results.SolidsOnly
        Q = items(cellfun(@(t) any(strcmp(t, solids)), typ(items)));
    else
        Q = items(~cellfun(@(t) any(strcmp(t, skip)), typ(items)));
    end
    vis = false(N, 1); vis(Q) = true; loc = zeros(0, 3);
    while ~isempty(Q)
        id = Q(end); Q(end) = [];
        switch typ{id}
            case 'VERTEX_POINT'                       % topological vertices lie on the solid
                loc(end+1, :) = pts(refs{id}(1), :); %#ok<AGROW>
            case 'EDGE_CURVE'
                % (start vertex, end vertex, curve, same_sense): the vertices are queued; a circular
                % edge is sampled along its ARC only (a full circle would overshoot trimmed shells,
                % e.g. the flat dribbler face cut into the r = 88 mm cylinder); other curves (lines,
                % B-splines) are bounded by their vertices
                rr = refs{id}; v = rr(1:2); v = v(~vis(v)); vis(v) = true; Q = [Q v];
                cv = rr(3);
                if any(strcmp(typ{cv}, {'SURFACE_CURVE', 'SEAM_CURVE', 'BOUNDED_SURFACE_CURVE'})), cv = refs{cv}(1); end
                if strcmp(typ{cv}, 'CIRCLE')
                    Pa = P{refs{cv}(1)}; r = str2double(regexp(args{cv}, ',([-+0-9.Ee]+)\)$', 'tokens', 'once'));
                    l1 = Pa \ [pts(refs{rr(1)}(1), :)'; 1]; l2 = Pa \ [pts(refs{rr(2)}(1), :)'; 1];
                    a1 = atan2(l1(2), l1(1)); a2 = atan2(l2(2), l2(1));
                    if rr(1) == rr(2)
                        a = linspace(0, 2*pi, 13); a(end) = [];
                    elseif ~isempty(regexp(args{id}, '\.T\.\)$', 'once'))
                        if a2 <= a1, a2 = a2 + 2*pi; end
                        a = linspace(a1, a2, 9);
                    else
                        if a2 >= a1, a2 = a2 - 2*pi; end
                        a = linspace(a1, a2, 9);
                    end
                    c = (Pa * [r*cos(a); r*sin(a); zeros(size(a)); ones(size(a))])'; loc = [loc; c(:, 1:3)]; %#ok<AGROW>
                end
            case {'CARTESIAN_POINT', 'AXIS2_PLACEMENT_3D', 'CIRCLE'}
                % a point reached directly is a B-spline control point or a surface origin (may lie
                % far off the solid); placements and untrimmed curves are not part of the extent
            otherwise
                nx = refs{id}; nx = nx(~vis(nx)); vis(nx) = true; Q = [Q nx];
        end
    end
    if isempty(loc), continue; end
    w = (Tx * s.T * [loc'; ones(1, size(loc, 1))])'; w = w(:, 1:3);
    allP = [allP; w]; %#ok<AGROW>
    rows(end+1, :) = {s.path, size(w, 1), min(w), max(w), max(w) - min(w)}; %#ok<AGROW>
end
rows(end+1, :) = {'ASSEMBLY', size(allP, 1), min(allP), max(allP), max(allP) - min(allP)};
T = cell2table(rows, 'VariableNames', {'path', 'n', 'lo', 'hi', 'size'});

if ~ip.Results.Quiet
    [~, nm, ext] = fileparts(stepFile);
    fprintf('\n== %s%s: %d entities, %d occurrences, %d leaf parts\n', nm, ext, numel(ids), numel(occ), height(T) - 1);
    for i = 1:height(T)
        fprintf('  %-45s n=%6d  lo [%8.2f %8.2f %8.2f]  hi [%8.2f %8.2f %8.2f]  size [%7.2f %7.2f %7.2f]\n', ...
            T.path{i}, T.n(i), T.lo(i, :), T.hi(i, :), T.size(i, :));
    end
end
end
