function cache = build_event_cache(events, opts)
%BUILD_EVENT_CACHE Pre-carrega (canonical_split+load_split) os eventos UMA vez
% para reuso em bo_cost (evita reler parquet a cada avaliacao do bayesopt).
% events: cell Nx2 {label, event}. cache(i): label,event,s,t,xt,yt,tht.
arguments
    events cell
    opts.Dataset (1,:) char = '2026-05-18_19-2-15'
end
repo_root = bootstrap_paths();
cache = struct('label',{},'event',{},'s',{},'t',{},'xt',{},'yt',{},'tht',{});
for i = 1:size(events,1)
    lab = events{i,1}; ev = events{i,2};
    cmd = fullfile(repo_root,'data','extracted',opts.Dataset,'splits',lab,ev,'commands.parquet');
    s = load_split(canonical_split(cmd));
    cache(end+1) = struct('label',lab,'event',ev,'s',s,'t',s.t, ...
        'xt',s.pos_x_truth.Data,'yt',s.pos_y_truth.Data,'tht',s.theta_truth.Data); %#ok<AGROW>
end
fprintf('build_event_cache: %d eventos em cache\n', numel(cache));
end
