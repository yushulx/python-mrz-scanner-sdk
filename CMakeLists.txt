cmake_minimum_required(VERSION 3.4...3.22)

project(mrzscanner)

find_package(PythonExtensions REQUIRED)

if(CMAKE_HOST_UNIX)
    SET(CMAKE_CXX_FLAGS "-std=c++11 -O3 -Wl,-rpath=$ORIGIN")
    SET(CMAKE_INSTALL_RPATH "$ORIGIN")
    SET(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)
endif()

MESSAGE( STATUS "CPU architecture ${CMAKE_SYSTEM_PROCESSOR}" )
if(CMAKE_HOST_WIN32)
    link_directories("${PROJECT_SOURCE_DIR}/lib/win/") 
elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    MESSAGE( STATUS "Link directory: ${PROJECT_SOURCE_DIR}/lib/linux/" )
    link_directories("${PROJECT_SOURCE_DIR}/lib/linux/")
endif()
include_directories("${PROJECT_BINARY_DIR}" "${PROJECT_SOURCE_DIR}/include/")

add_library(${PROJECT_NAME} MODULE src/mrzscanner.cpp)
if(CMAKE_HOST_WIN32)
    target_link_libraries(${PROJECT_NAME} "DynamsoftLabelRecognizerx64")
else()
    target_link_libraries(${PROJECT_NAME} "DynamsoftLabelRecognizer")
endif()

if(CMAKE_HOST_WIN32)
    add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD 
    COMMAND ${CMAKE_COMMAND} -E copy_directory
    "${PROJECT_SOURCE_DIR}/lib/win/"      
    $<TARGET_FILE_DIR:${PROJECT_NAME}>)
endif()

python_extension_module(mrzscanner)
install(TARGETS mrzscanner LIBRARY DESTINATION mrzscanner)

if(CMAKE_HOST_WIN32)
    install (DIRECTORY  "${PROJECT_SOURCE_DIR}/lib/win/" DESTINATION mrzscanner)
elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    install (DIRECTORY  "${PROJECT_SOURCE_DIR}/lib/linux/" DESTINATION mrzscanner)
endif()

install (FILES  "${PROJECT_SOURCE_DIR}/MRZ.json" DESTINATION mrzscanner)
install (DIRECTORY  "${PROJECT_SOURCE_DIR}/model" DESTINATION mrzscanner/model)