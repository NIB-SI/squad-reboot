function [] = drawStatesFromFile(v,filename,numCol)
%Input: row vector with numbers corresponding to the external stimuli to be
%plotted from the file filename which has to be given as a string
%'filename', number numCol number of external stimuli in a row in
%the plot
%Output: plot of the states

A=importdata(filename);         %Imports the data from filename
timeSteps=A(1,:);               %time steps
x=A(2:end,:);                   %time curves of states    

numPlots=max(size(v));          %Number of plots
numRows=ceil(numPlots/numCol);  %Rounds to the next greater integer to get number of rows for the plot in which the states are plotted

image=figure('name','Plot of states','NumberTitle','off');        %Creates figure for the plot
panel=uipanel('Parent',image,'BorderType','none');
for i=1:numPlots                                                  %Plots each graph of all external stimuli indexed with v(1,i) in a different subplot
    subplot(numRows,numCol,i,'Parent',panel)
    plot(timeSteps,x(v(1,i),:));                                  %Plot of the states x(v(1,i),:) over timeSteps
    titleplot=sprintf('$x_{%i}$',v(1,i));                         %Creates the title of each subplot consisting of x_i where i is an element of v
    title(titleplot,'Interpreter','latex')
end

end


