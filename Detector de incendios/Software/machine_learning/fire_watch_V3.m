data = readtable('dataset_FW.xlsx');
disp(data.Properties.VariableNames);

Y = data.CLASE;

% Dividir datos en entrenamiento y prueba
cv = cvpartition(height(data), 'HoldOut', 0.3);
X_train = X(training(cv), :);
Y_train = Y(training(cv));
X_test = X(test(cv), :);
Y_test = Y(test(cv));

% Entrenar modelo de regresión logística
trainedModel = fitglm(X_train, Y_train, 'linear', 'Distribution', 'binomial');

% Verificar rendimiento en los datos de prueba
predictions = round(predict(trainedModel, X_test));
accuracy = mean(predictions == Y_test);
disp(['Precisión del modelo: ', num2str(accuracy)]);

% Obtener los pesos y sesgo del modelo
weights = trainedModel.Coefficients.Estimate(2:end); % Pesos (omitimos el término independiente)
bias = trainedModel.Coefficients.Estimate(1);       % Sesgo

% Guardar en un archivo .mat
save('fire_watch_V4.mat', 'weights', 'bias');

