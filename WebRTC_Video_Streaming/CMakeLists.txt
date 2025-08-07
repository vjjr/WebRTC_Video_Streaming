cmake_minimum_required(VERSION 3.16)
project(WebRTCVideoStreamingStub)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Add preprocessor definitions for Windows
add_definitions(
    -DWEBRTC_WIN
    -DNOMINMAX
    -DWIN32_LEAN_AND_MEAN
    -D_WIN32_WINNT=0x0A00
    -DWINVER=0x0A00
    -DWEBRTC_STUB_BUILD
)

# Create the executable
add_executable(webrtc_native_client
    simple_webrtc_client_stub.cpp
)

# Windows specific libraries
if(WIN32)
    target_link_libraries(webrtc_native_client
        ws2_32
        winmm
        dnsapi
        version
        msimg32
        oleaut32
        shell32
        shlwapi
        vfw32
        secur32
        amstrmid
        msdmo
        dmoguids
        wmcodecdspuuid
        ole32
        strmiids
    )
endif()

# Set output directory
set_target_properties(webrtc_native_client PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)

message(STATUS "=== WebRTC Native Client - Stub Build ===")
message(STATUS "This demonstrates the native WebRTC structure")
message(STATUS "No WebRTC libraries required!")
message(STATUS "Shows how the real implementation would work")
message(STATUS "===========================================")
