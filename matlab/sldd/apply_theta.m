function apply_theta(sldd_path, theta)
if isnumeric(theta)
    % Converte vetor pra struct usando convenção padrão
    NAMES = {'K_vx','tau_vx','Td_vx','K_vy','tau_vy','Td_vy', ...
        'K_w','tau_w','Td_w'};
    theta = cell2struct(num2cell(theta(:).'), NAMES, 2);
end

dd  = Simulink.data.dictionary.open(sldd_path);
sec = getSection(dd, 'Design Data');
fn  = fieldnames(theta);
for k = 1:numel(fn)
    e = getEntry(sec, fn{k});
    v = getValue(e);  v.Value = theta.(fn{k});  setValue(e, v);
end
saveChanges(dd); close(dd);
end